"""Ollama·Claude 어댑터 검사. 가짜 통신기·가짜 클라이언트만 쓰며 실제 호출·과금이 없다."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.ai.claude import ClaudeGeneration
from app.ai.config import read_ai_settings
from app.ai.interfaces import EmbeddingRequest, GenerationRequest, ProviderCallError
from app.ai.ollama import OllamaEmbedding, OllamaGeneration
from app.pipeline.analyze import analyze
from app.pipeline.pending_analysis import DEFAULT_TIMEOUT, call_timeout
from app.schemas.mail_analysis import AnalysisResult
from tests.f1.support import CASES, sample_mail

SECRET_BODY = "합성 본문-노출 금지 표식"
REQUEST = GenerationRequest(
    purpose="analysis",
    system_prompt="시스템",
    user_prompt=SECRET_BODY,
    response_schema={"type": "object", "properties": {}, "additionalProperties": False},
)


def run(coroutine):
    return asyncio.run(coroutine)


def ollama(handler, **env):
    settings = read_ai_settings({"AI_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen-test", **env})
    transport = httpx.MockTransport(handler)
    return (
        OllamaGeneration(settings.ollama, transport=transport),
        OllamaEmbedding(settings.embedding, settings.ollama.base_url, transport=transport),
    )


def chat_reply(content):
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


def test_ollama_chat_request_shape_and_clean_output():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert request.url == "http://localhost:11434/api/chat"
        return chat_reply('<think>…</think>```json\n{"ok": true}\n```')

    generation, _ = ollama(handler, OLLAMA_THINK="false")
    assert run(generation.generate(REQUEST)) == '{"ok": true}'
    body = seen[0]
    assert body["model"] == "qwen-test" and body["stream"] is False
    assert body["format"] == REQUEST.response_schema and body["think"] is False
    assert body["options"] == {"temperature": 0}
    assert body["messages"][1]["content"] == SECRET_BODY


@pytest.mark.parametrize(("mode", "expected"), [("json", "json"), ("none", None)])
def test_ollama_format_modes(mode, expected):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return chat_reply("{}")

    generation, _ = ollama(handler, OLLAMA_FORMAT=mode)
    run(generation.generate(REQUEST))
    assert seen[0].get("format") == expected and "think" not in seen[0]


def test_ollama_retries_connection_and_timeout_then_gives_fixed_guidance():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("refused", request=request)

    generation, _ = ollama(handler, OLLAMA_RETRIES="2")
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert len(calls) == 3 and error.value.code == "ollama_unreachable"
    assert "ollama serve" in str(error.value) and SECRET_BODY not in str(error.value)

    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    generation, _ = ollama(slow)
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert error.value.code == "ollama_timeout"


def test_ollama_recovers_after_one_transient_failure():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, json={"error": "loading"})
        return chat_reply("{}")

    generation, _ = ollama(handler)
    assert run(generation.generate(REQUEST)) == "{}" and len(calls) == 2


def test_ollama_missing_model_and_bad_request_are_not_retried():
    calls = []

    def missing(request):
        calls.append(1)
        return httpx.Response(404, json={"error": f"model not found {SECRET_BODY}"})

    generation, _ = ollama(missing)
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert len(calls) == 1 and error.value.code == "ollama_model_not_found"
    assert "ollama pull qwen-test" in str(error.value) and SECRET_BODY not in str(error.value)

    generation, _ = ollama(lambda request: httpx.Response(400, json={"error": "think"}))
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert error.value.code == "ollama_bad_request"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=[1]),
        httpx.Response(200, json={"message": {"content": 3}}),
    ],
)
def test_ollama_unreadable_response(response):
    generation, _ = ollama(lambda request: response)
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert error.value.code == "ollama_invalid_response"


def test_ollama_proxy_environment_is_ignored(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:1")
    monkeypatch.setenv("ALL_PROXY", "http://proxy.invalid:1")
    generation, _ = ollama(lambda request: chat_reply("{}"))
    assert run(generation.generate(REQUEST)) == "{}"


def test_ollama_embedding_request_and_response():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[0.1] * 4, [0.2] * 4]})

    _, embedding = ollama(handler, EMBEDDING_DIMENSIONS="4")
    vectors = run(embedding.embed(EmbeddingRequest(texts=("가", "나"))))
    assert seen[0] == {"model": "bge-m3", "input": ["가", "나"], "truncate": True}
    assert len(vectors) == 2 and embedding.dimensions == 4
    assert embedding.identity.provider == "ollama" and embedding.call_timeout > DEFAULT_TIMEOUT

    _, broken = ollama(lambda request: httpx.Response(200, json={"embeddings": None}))
    with pytest.raises(ProviderCallError):
        run(broken.embed(EmbeddingRequest(texts=("가",))))


def test_pipeline_uses_provider_timeouts_for_slow_local_models():
    generation, _ = ollama(lambda request: chat_reply("{}"), OLLAMA_TIMEOUT_SECONDS="300")
    assert call_timeout(generation) == 300 * 2 + 5
    assert call_timeout(object()) == DEFAULT_TIMEOUT
    assert call_timeout(SimpleNamespace(call_timeout=True)) == DEFAULT_TIMEOUT


def test_ollama_end_to_end_analysis_with_retry_on_invalid_json():
    case = CASES[0]
    replies = iter(["형식 위반", json.dumps(case["expected"], ensure_ascii=False)])
    generation, _ = ollama(lambda request: chat_reply(next(replies)))
    result, attempts = run(analyze(sample_mail(0), generation))
    assert attempts == 2 and isinstance(result, AnalysisResult)


# ---- Claude (가짜 클라이언트: 실제 API·키·과금 없음) ----

CLAUDE_ENV = {
    "AI_PROVIDER": "claude",
    "ANTHROPIC_API_KEY": "synthetic-not-a-real-key",
    "AI_CLAUDE_TEST_DATA_ONLY": "true",
}


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def claude(response=None, error=None, **env):
    messages = FakeMessages(response, error)
    settings = read_ai_settings({**CLAUDE_ENV, **env}).claude
    return ClaudeGeneration(settings, client=SimpleNamespace(messages=messages)), messages


def message(*blocks, stop_reason="end_turn"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


def text(value):
    return SimpleNamespace(type="text", text=value)


def test_claude_request_uses_structured_output_effort_and_no_fallbacks():
    generation, messages = claude(
        message(SimpleNamespace(type="thinking", thinking=""), text('{"ok": true}')),
        CLAUDE_MODEL_ANALYSIS="claude-haiku-5-5",
    )
    schema = AnalysisResult.model_json_schema()
    request = GenerationRequest("analysis", "시스템", SECRET_BODY, schema)
    assert run(generation.generate(request)) == '{"ok": true}'
    call = messages.calls[0]
    assert call["model"] == "claude-haiku-5-5" and call["max_tokens"] == 16000
    assert call["system"] == "시스템"
    assert call["messages"] == [{"role": "user", "content": SECRET_BODY}]
    assert call["output_config"]["effort"] == "low"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "maxLength" not in str(call["output_config"]["format"]["schema"])
    # 비용 예측을 위해 거절 시 다른 모델로 넘기는 기능·thinking 끄기·beta를 보내지 않는다.
    assert not {"fallbacks", "betas", "thinking"} & call.keys()
    assert generation.identity.provider == "anthropic" and generation.external_transfer


@pytest.mark.parametrize(
    ("stop_reason", "code"), [("refusal", "claude_refused"), ("max_tokens", "claude_truncated")]
)
def test_claude_refusal_and_truncation_become_fixed_errors(stop_reason, code):
    generation, _ = claude(message(text("{"), stop_reason=stop_reason))
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert error.value.code == code


def test_claude_without_text_block_is_invalid():
    generation, _ = claude(message(SimpleNamespace(type="thinking", thinking="")))
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert error.value.code == "claude_invalid_response"


def test_claude_errors_never_leak_key_or_mail():
    generation, _ = claude(error=RuntimeError(f"synthetic-not-a-real-key {SECRET_BODY}"))
    with pytest.raises(ProviderCallError) as error:
        run(generation.generate(REQUEST))
    assert error.value.code == "claude_error" and error.value.__cause__ is None
    for secret in ("synthetic-not-a-real-key", SECRET_BODY):
        assert secret not in str(error.value)


def test_claude_sdk_error_classes_map_to_guidance():
    anthropic = pytest.importorskip("anthropic", reason="anthropic 의존성 패치 적용 전")
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    cases = [
        (anthropic.APITimeoutError(request=request), "claude_timeout"),
        (anthropic.APIConnectionError(request=request), "claude_unreachable"),
    ]
    for status, code in (
        (401, "claude_auth_failed"),
        (429, "claude_rate_limited"),
        (404, "claude_model_not_found"),
        (400, "claude_bad_request"),
    ):
        response = httpx.Response(status, request=request, json={"error": {}})
        cases.append((_status_error(anthropic, status, response), code))
    for error_value, code in cases:
        generation, _ = claude(error=error_value)
        with pytest.raises(ProviderCallError) as error:
            run(generation.generate(REQUEST))
        assert error.value.code == code


def _status_error(anthropic, status, response):
    kind = {
        401: anthropic.AuthenticationError,
        429: anthropic.RateLimitError,
        404: anthropic.NotFoundError,
        400: anthropic.BadRequestError,
    }[status]
    return kind("synthetic", response=response, body=None)


def test_real_claude_client_is_created_only_with_installed_sdk():
    pytest.importorskip("anthropic", reason="anthropic 의존성 패치 적용 전")
    from app.ai.runtime import load_generation

    generation = load_generation(CLAUDE_ENV)
    assert generation.client is not None and generation.identity.model == "claude-opus-5-5"


def test_real_sdk_request_shape_against_local_fake_server():
    """설치된 anthropic SDK로 실제 요청 모양을 만들되, 가짜 통신기로 받아 외부로 보내지 않는다."""
    anthropic = pytest.importorskip("anthropic", reason="anthropic 의존성 패치 적용 전")
    httpx2 = pytest.importorskip("httpx2")
    seen = []

    def handler(request):
        seen.append((str(request.url), json.loads(request.content)))
        return httpx2.Response(
            200,
            json={
                "id": "msg_synthetic",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": [
                    {"type": "thinking", "thinking": "", "signature": "sig"},
                    {"type": "text", "text": '{"ok": true}'},
                ],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    settings = read_ai_settings(CLAUDE_ENV).claude
    client = anthropic.AsyncAnthropic(
        api_key=settings.api_key,
        base_url="http://fake-anthropic.invalid",
        max_retries=0,
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    generation = ClaudeGeneration(settings, client=client)
    assert run(generation.generate(REQUEST)) == '{"ok": true}'
    url, body = seen[0]
    assert url == "http://fake-anthropic.invalid/v1/messages"
    assert body["model"] == "claude-opus-5-5" and body["output_config"]["effort"] == "low"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert "fallbacks" not in body and "thinking" not in body
