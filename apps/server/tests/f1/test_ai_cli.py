"""외부 전송 차단과 AI 확인 명령 검사. 실제 호출·DB·과금이 없다."""

import json

import httpx
import pytest

from app.ai import ollama as ollama_module
from app.cli import analyze_pending, check_ai

CLAUDE_ENV = {
    "AI_PROVIDER": "claude",
    "ANTHROPIC_API_KEY": "synthetic-not-a-real-key",
    "AI_CLAUDE_TEST_DATA_ONLY": "true",
}
OLLAMA_ENV = {"AI_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen-test", "EMBEDDING_DIMENSIONS": "3"}


class ExternalGeneration:
    external_transfer = True


class LocalGeneration:
    external_transfer = False


def reject_database():
    pytest.fail("차단·미설정 경로에서 DB를 열면 안 됩니다")


def test_claude_with_real_gmail_content_is_blocked_before_database(monkeypatch, capsys):
    monkeypatch.setattr(analyze_pending, "load_providers", lambda: (ExternalGeneration(), object()))
    monkeypatch.setattr(analyze_pending, "database_engine", reject_database)
    code = analyze_pending.main(
        ["run", "--user-id", "u", "--account-id", "a", "--allow-gmail-content"]
    )
    output = json.loads(capsys.readouterr().out)
    assert code == 1 and output["status"] == "external_transfer_blocked"
    assert "Ollama" in output["reason"]


def test_local_provider_is_not_blocked_for_gmail_content(monkeypatch, capsys):
    opened = []

    def database():
        opened.append(True)
        raise analyze_pending.DatabaseConfigurationError("test")

    monkeypatch.setattr(analyze_pending, "load_providers", lambda: (LocalGeneration(), object()))
    monkeypatch.setattr(analyze_pending, "database_engine", database)
    analyze_pending.main(["run", "--user-id", "u", "--account-id", "a", "--allow-gmail-content"])
    assert opened and json.loads(capsys.readouterr().out)["status"] == "storage_unavailable"


def test_configuration_error_reason_has_no_secret(monkeypatch, capsys):
    monkeypatch.setattr(
        "app.ai.config.environment_values",
        lambda: {**CLAUDE_ENV, "AI_CLAUDE_TEST_DATA_ONLY": ""},
    )
    monkeypatch.setattr(analyze_pending, "database_engine", reject_database)
    assert analyze_pending.main(["run", "--user-id", "u", "--account-id", "a"]) == 1
    raw = capsys.readouterr().out
    assert "AI_CLAUDE_TEST_DATA_ONLY" in raw and "synthetic-not-a-real-key" not in raw


def test_check_ai_reports_not_configured(capsys):
    assert check_ai.main([], values={}) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "not_configured"


def test_check_ai_without_ping_makes_no_network_call(monkeypatch, capsys):
    def no_network(*args, **kwargs):
        pytest.fail("--ping 없이 네트워크를 쓰면 안 됩니다")

    monkeypatch.setattr(ollama_module._OllamaClient, "post", no_network)
    assert check_ai.main([], values=OLLAMA_ENV) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "status": "configured",
        "provider": "ollama",
        "generation_model": "qwen-test",
        "embedding_model": "bge-m3",
        "embedding_dimensions": 3,
        "external_transfer": False,
    }


def fake_ollama(monkeypatch, handler):
    original = ollama_module._OllamaClient.__init__

    def init(self, base_url, timeout, retries, transport=None):
        original(self, base_url, timeout, 0, httpx.MockTransport(handler))

    monkeypatch.setattr(ollama_module._OllamaClient, "__init__", init)


def test_check_ai_ping_success(monkeypatch, capsys):
    def handler(request):
        if request.url.path == "/api/chat":
            return httpx.Response(200, json={"message": {"content": '{"ok": true}'}})
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})

    fake_ollama(monkeypatch, handler)
    assert check_ai.main(["--ping"], values=OLLAMA_ENV) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "reachable"
    assert output["generation"] == output["embedding"] == "ok"


def test_check_ai_ping_gives_guidance_on_failure(monkeypatch, capsys):
    def handler(request):
        if request.url.path == "/api/chat":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    fake_ollama(monkeypatch, handler)
    assert check_ai.main(["--ping"], values=OLLAMA_ENV) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "unreachable"
    assert (
        output["generation"] == "ollama_unreachable" and "ollama serve" in output["generation_hint"]
    )
    assert output["embedding"] == "dimension_mismatch"
