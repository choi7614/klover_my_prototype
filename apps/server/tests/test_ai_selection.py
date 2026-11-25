"""외부 호출 없이 설정 암호화·명시적 선택·요청 격리와 인증을 검증한다."""

import asyncio
import json
import stat
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ai.config import AIConfigurationError, read_ai_settings
from app.ai.interfaces import GenerationRequest, ProviderCallError
from app.ai.selection import (
    AISelectionError,
    AISettingsStore,
    AIUpdate,
    Defaults,
    SelectedGeneration,
    selected,
)
from app.api.mail_read import MailAPIContext
from app.main import create_app

KEY = "synthetic-api-key-never-real"
TOKEN = "T" * 43
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def settings(tmp_path, **values):
    return AISettingsStore(
        tmp_path / "secrets", values={"OLLAMA_MODEL": "synthetic-local", **values}
    )


def update(store, *, consent=True, defaults=None, key=KEY):
    return store.update(
        AIUpdate(
            mode="hybrid", defaults=defaults or Defaults(), external_consent=consent, api_key=key
        )
    )


def request(purpose="draft"):
    return GenerationRequest(
        purpose=purpose, system_prompt="synthetic", user_prompt="synthetic", response_schema={}
    )


def test_encrypted_settings_survive_restart_and_never_return_key(tmp_path):
    store = settings(tmp_path)
    before = store.state()
    assert not before.claude_key_set and not store.directory.exists()
    state = update(store, defaults=Defaults(draft="claude", weekly_report="claude"))
    assert state.claude_key_set
    assert KEY not in state.model_dump_json()
    assert KEY.encode() not in (store.directory / "ai-settings.enc").read_bytes()
    for name in ("ai-settings.key", "ai-settings.enc"):
        assert stat.S_IMODE((store.directory / name).stat().st_mode) == 0o600
    assert settings(tmp_path).state() == state
    store.update(AIUpdate(mode="hybrid", defaults=Defaults(), external_consent=False))
    assert store.state().claude_key_set  # 빈 입력은 기존 키를 유지한다.


def test_corrupt_or_missing_cipher_key_fails_without_overwriting_files(tmp_path):
    store = settings(tmp_path)
    update(store)
    encrypted = (store.directory / "ai-settings.enc").read_bytes()
    (store.directory / "ai-settings.key").unlink()
    with pytest.raises(AISelectionError):
        store.read()
    assert not (store.directory / "ai-settings.key").exists()
    assert (store.directory / "ai-settings.enc").read_bytes() == encrypted


def test_no_consent_never_constructs_external_provider(tmp_path):
    store = settings(tmp_path)
    update(store, consent=False)

    def forbidden(_values):
        pytest.fail("외부 제공자를 만들면 안 됨")

    router = SelectedGeneration(store, loader=forbidden)

    async def run():
        with selected(store, "claude"), pytest.raises(AISelectionError):
            await router.generate(request())

    asyncio.run(run())


def test_defaults_overrides_simultaneous_calls_and_two_stage_snapshot(tmp_path):
    store = settings(tmp_path)
    update(store, defaults=Defaults(draft="claude", search="ollama", weekly_report="claude"))
    seen = []

    def loader(values):
        provider = values["AI_PROVIDER"]
        if provider == "claude":
            assert values["ANTHROPIC_API_KEY"] == KEY
            assert values["AI_CLAUDE_EXTERNAL_CONSENT"] == "true"

        async def generate(r):
            await asyncio.sleep(0)
            seen.append((r.purpose, provider))
            return provider

        return SimpleNamespace(generate=generate)

    router = SelectedGeneration(store, loader=loader)

    async def call(choice, purpose):
        with selected(store, choice):
            return await router.generate(request(purpose))

    async def run():
        assert await asyncio.gather(
            call("ollama", "draft"), call("claude", "search"), call(None, "weekly_report")
        ) == ["ollama", "claude", "claude"]
        with selected(store):
            assert await router.generate(request("search")) == "ollama"
            update(store, defaults=Defaults(search="claude"))
            assert await router.generate(request("search")) == "ollama"
        assert await call(None, "search") == "claude"

    asyncio.run(run())
    assert len(seen) == 6


def test_two_provider_errors_are_bounded_and_auto_purposes_are_blocked(tmp_path):
    store = settings(tmp_path)
    update(store)
    calls = []

    def loader(values):
        calls.append(values["AI_PROVIDER"])

        async def fail(_request):
            raise ProviderCallError(code="claude_rate_limited")

        return SimpleNamespace(generate=fail)

    router = SelectedGeneration(store, loader=loader)

    async def run():
        with selected(store, "claude"), pytest.raises(ProviderCallError):
            await router.generate(request())
        for purpose in ("analysis", "scan"):
            with pytest.raises(AISelectionError):
                await router.generate(request(purpose))

    asyncio.run(run())
    assert calls == ["claude", "ollama"]


def test_real_mail_consent_is_separate_from_synthetic_test_flag():
    result = read_ai_settings(
        {"AI_PROVIDER": "claude", "ANTHROPIC_API_KEY": KEY, "AI_CLAUDE_EXTERNAL_CONSENT": "true"}
    )
    assert result.provider == "claude"
    with pytest.raises(AIConfigurationError):
        read_ai_settings({"AI_PROVIDER": "claude", "ANTHROPIC_API_KEY": KEY})


def client(store):
    app = create_app()
    app.state.ai_settings = store
    app.state.mail_api = MailAPIContext(TOKEN, object())
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 10101))


def test_settings_api_auth_validation_and_secret_redaction(tmp_path):
    store = settings(tmp_path)
    with client(store) as http:
        assert http.get("/settings/ai").status_code == 401
        assert (
            http.get("/settings/ai", headers={**AUTH, "Origin": "http://evil.invalid"}).status_code
            == 403
        )
        body = {
            "defaults": Defaults(draft="claude").model_dump(),
            "external_consent": True,
            "api_key": KEY,
        }
        response = http.put("/settings/ai", json=body, headers=AUTH)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert KEY not in response.text and response.json()["claude_key_set"]
        assert http.get("/settings/ai", headers=AUTH).json() == response.json()
        bad = http.put("/settings/ai", json={**body, "defaults": {"draft": KEY}}, headers=AUTH)
        assert bad.status_code == 422 and KEY not in bad.text
        assert (
            http.post("/settings/ai/check", json={"provider": KEY}, headers=AUTH).status_code == 422
        )


def test_connection_probe_is_synthetic_and_requires_saved_consent(tmp_path, monkeypatch):
    store = settings(tmp_path)
    update(store)
    captured = []

    async def fake_generate(self, request):
        captured.append(request)
        return '{"ok":true}'

    monkeypatch.setattr(SelectedGeneration, "generate", fake_generate)
    with client(store) as http:
        response = http.post("/settings/ai/check", json={"provider": "claude"}, headers=AUTH)
        assert response.json() == {"status": "reachable", "provider": "claude"}
    assert json.loads(captured[0].user_prompt) == {"test": "connection-only; no mail data"}


@pytest.mark.parametrize(
    "provider,failure,code,hint",
    [
        (
            "claude",
            ProviderCallError("private-detail", code="claude_auth_failed"),
            "claude_auth_failed",
            "키가 올바르지",
        ),
        (
            "claude",
            ProviderCallError("private-detail", code="claude_model_not_found"),
            "claude_model_not_found",
            "모델 ID",
        ),
        (
            "claude",
            ProviderCallError("private-detail", code="claude_rate_limited"),
            "claude_rate_limited",
            "잔액",
        ),
        (
            "claude",
            ProviderCallError("private-detail", code="claude_unreachable"),
            "claude_unreachable",
            "인터넷",
        ),
        (
            "claude",
            ProviderCallError("private-detail", code="claude_credit_low"),
            "claude_credit_low",
            "크레딧",
        ),
        (
            "claude",
            ProviderCallError("private-detail", code="claude_format_unsupported"),
            "claude_format_unsupported",
            "JSON",
        ),
        ("claude", TimeoutError(), "claude_timeout", "늦어요"),
        (
            "claude",
            ProviderCallError("private-detail", code="unknown-code"),
            "claude_error",
            "실패",
        ),
        (
            "ollama",
            ProviderCallError("private-detail", code="ollama_unreachable"),
            "ollama_unreachable",
            "Ollama",
        ),
        (
            "ollama",
            ProviderCallError("private-detail", code="ollama_model_not_found"),
            "ollama_model_not_found",
            "ollama pull",
        ),
        ("ollama", TimeoutError(), "ollama_timeout", "늦어요"),
    ],
)
def test_connection_probe_failure_says_the_cause_in_fixed_words(
    tmp_path, monkeypatch, provider, failure, code, hint
):
    store = settings(tmp_path)
    update(store)

    async def fail(self, request):
        raise failure

    monkeypatch.setattr(SelectedGeneration, "generate", fail)
    with client(store) as http:
        response = http.post("/settings/ai/check", json={"provider": provider}, headers=AUTH)
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == code and hint in error["message"]
    # 제공자가 준 상세 문장·키는 응답에 섞이지 않는다.
    assert "private-detail" not in response.text and KEY not in response.text


def test_connection_probe_failure_adds_the_providers_reason_without_the_key(tmp_path, monkeypatch):
    store = settings(tmp_path)
    update(store)

    async def fail(self, request):
        raise ProviderCallError(
            "고정", code="claude_bad_request", detail="model: not available for this workspace"
        )

    monkeypatch.setattr(SelectedGeneration, "generate", fail)
    with client(store) as http:
        response = http.post("/settings/ai/check", json={"provider": "claude"}, headers=AUTH)
    message = response.json()["error"]["message"]
    assert "Anthropic 안내: model: not available for this workspace" in message
    assert KEY not in response.text


def test_provider_reason_is_cleaned_of_keys_and_limited():
    from app.ai.claude import safe_detail

    error = SimpleNamespace(message=f"bad {KEY}\n  and sk-ant-api03-abcdefghijk " + "x" * 500)
    text = safe_detail(error, (KEY,))
    assert KEY not in text and "sk-ant" not in text and "\n" not in text and len(text) <= 200
    assert safe_detail(RuntimeError("no message attr")) == ""


def test_claude_models_lists_only_claude_ids_for_the_saved_key(tmp_path, monkeypatch):
    store = settings(tmp_path)
    update(store)
    seen = []

    async def fake_list(key, **kwargs):
        seen.append(key)
        return [
            {"id": "claude-sonnet-5-5", "name": "Claude Sonnet 5.5"},
            {"id": "not-claude-model", "name": "x"},
            {"id": "claude-opus-5-5", "name": "Claude Opus 5.5"},
        ]

    monkeypatch.setattr("app.api.ai_settings.list_models", fake_list)
    with client(store) as http:
        assert http.get("/settings/ai/claude-models").status_code == 401
        response = http.get("/settings/ai/claude-models", headers=AUTH)
    assert [m["id"] for m in response.json()["models"]] == ["claude-sonnet-5-5", "claude-opus-5-5"]
    assert seen == [KEY] and KEY not in response.text


def test_claude_models_reports_missing_key_local_mode_and_provider_failure(tmp_path, monkeypatch):
    store = settings(tmp_path)
    update(store, key=None)
    with client(store) as http:
        error = http.get("/settings/ai/claude-models", headers=AUTH).json()["error"]
        assert error["code"] == "claude_key_missing"

    async def fail(key, **kwargs):
        raise ProviderCallError("고정", code="claude_auth_failed", detail="invalid x-api-key")

    monkeypatch.setattr("app.api.ai_settings.list_models", fail)
    update(store)
    with client(store) as http:
        error = http.get("/settings/ai/claude-models", headers=AUTH).json()["error"]
        assert error["code"] == "claude_auth_failed" and "invalid x-api-key" in error["message"]
    store.update(
        AIUpdate(mode="local_only", defaults=Defaults(), external_consent=True, api_key=KEY)
    )
    with client(store) as http:
        assert http.get("/settings/ai/claude-models", headers=AUTH).status_code == 503


def test_connection_probe_tells_when_claude_key_is_not_registered(tmp_path, monkeypatch):
    from app.ai.interfaces import ProvidersNotConfigured

    store = settings(tmp_path)
    update(store, key=None)

    async def fail(self, request):
        raise ProvidersNotConfigured("private-detail")

    monkeypatch.setattr(SelectedGeneration, "generate", fail)
    with client(store) as http:
        error = http.post("/settings/ai/check", json={"provider": "claude"}, headers=AUTH).json()[
            "error"
        ]
    assert error["code"] == "claude_key_missing" and "키가 등록되지 않았어요" in error["message"]


def test_model_setting_is_saved_and_used_only_for_selected_claude_calls(tmp_path):
    store = settings(tmp_path, CLAUDE_MODEL_DRAFT="old-synthetic-model")
    store.update(
        AIUpdate(
            mode="hybrid",
            defaults=Defaults(draft="claude"),
            external_consent=True,
            api_key=KEY,
            claude_model="new-synthetic-model",
        )
    )
    captured = []

    def loader(values):
        captured.append(values)

        async def generate(_request):
            return "synthetic-result"

        return SimpleNamespace(generate=generate)

    async def run():
        with selected(store):
            await SelectedGeneration(store, loader=loader).generate(request())

    asyncio.run(run())
    assert captured[0]["CLAUDE_MODEL_DRAFT"] == "new-synthetic-model"
    assert store.state().claude_model == "new-synthetic-model"


def test_new_install_local_only_blocks_saved_and_explicit_claude_despite_environment(tmp_path):
    store = settings(
        tmp_path, AI_PROVIDER="claude", ANTHROPIC_API_KEY=KEY, AI_CLAUDE_EXTERNAL_CONSENT="true"
    )
    assert store.state().mode == "local_only"
    store.update(
        AIUpdate(
            mode="local_only", defaults=Defaults(draft="claude"), external_consent=True, api_key=KEY
        )
    )
    calls = []

    def loader(values):
        calls.append(values["AI_PROVIDER"])

        async def gen(_):
            return "synthetic"

        return SimpleNamespace(generate=gen)

    async def run():
        with selected(store):
            await SelectedGeneration(store, loader=loader).generate(request())
        with selected(store, "claude"), pytest.raises(AISelectionError):
            await SelectedGeneration(store, loader=loader).generate(request())

    asyncio.run(run())
    assert calls == ["ollama"]
    assert store.state().claude_key_set


def test_fallback_is_once_per_request_and_pins_remaining_search_stages_to_local(tmp_path):
    store = settings(tmp_path)
    update(store)
    calls = []

    def loader(values):
        calls.append(values["AI_PROVIDER"])

        async def gen(_):
            if values["AI_PROVIDER"] == "claude":
                raise ProviderCallError(code="claude_unreachable")
            return "synthetic"

        return SimpleNamespace(generate=gen)

    async def run():
        with selected(store, "claude") as trace:
            router = SelectedGeneration(store, loader=loader)
            await router.generate(request("search"))
            await router.generate(request("search"))
            assert trace["fallback"] and trace["reason"] == "claude_unreachable"

    asyncio.run(run())
    assert calls == ["claude", "ollama", "ollama"]


def test_probe_cannot_report_local_success_as_claude_connected(tmp_path):
    store = settings(tmp_path)
    update(store)
    calls = []

    def loader(values):
        calls.append(values["AI_PROVIDER"])

        async def gen(_):
            raise ProviderCallError(code="claude_auth_failed")

        return SimpleNamespace(generate=gen)

    async def run():
        with selected(store, "claude", fallback=False), pytest.raises(ProviderCallError):
            await SelectedGeneration(store, loader=loader).generate(request())

    asyncio.run(run())
    assert calls == ["claude"]


def test_local_mode_blocks_claude_probe_api_without_provider_construction(tmp_path, monkeypatch):
    store = settings(tmp_path)
    store.update(
        AIUpdate(
            mode="local_only", defaults=Defaults(draft="claude"), external_consent=True, api_key=KEY
        )
    )

    def forbidden(*args, **kwargs):
        pytest.fail("로컬 모드에서 Claude SDK 생성 금지")

    monkeypatch.setattr("app.ai.claude.ClaudeGeneration.__init__", forbidden)
    with client(store) as http:
        response = http.post("/settings/ai/check", json={"provider": "claude"}, headers=AUTH)
        assert response.status_code == 503
        assert KEY not in response.text


def test_cancelled_claude_request_does_not_start_local(tmp_path):
    store = settings(tmp_path)
    update(store)
    calls = []
    started = asyncio.Event()

    def loader(values):
        calls.append(values["AI_PROVIDER"])

        async def generate(_):
            started.set()
            await asyncio.Future()

        return SimpleNamespace(generate=generate)

    async def run():
        with selected(store, "claude"):
            task = asyncio.create_task(SelectedGeneration(store, loader=loader).generate(request()))
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(run())
    assert calls == ["claude"]
