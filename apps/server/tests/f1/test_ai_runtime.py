"""AI 제공자 선택·설정 검사. 실제 네트워크·키·과금 없이 실행한다."""

import pytest

from app.ai.config import AIConfigurationError, loopback_url, read_ai_settings
from app.ai.interfaces import ProvidersNotConfigured
from app.ai.json_output import clean_json_text, strict_schema
from app.ai.runtime import is_external, load_embedding, load_generation, load_providers
from app.schemas.mail_analysis import AnalysisResult

CLAUDE = {
    "AI_PROVIDER": "claude",
    "ANTHROPIC_API_KEY": "synthetic-not-a-real-key",
    "AI_CLAUDE_TEST_DATA_ONLY": "true",
}
OLLAMA = {"AI_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen-test:latest"}


def test_empty_provider_stays_not_configured_without_fake_results():
    assert read_ai_settings({}).provider is None
    for loader in (load_generation, load_embedding, load_providers):
        with pytest.raises(ProvidersNotConfigured):
            loader({})
    with pytest.raises(ProvidersNotConfigured):
        load_providers({"AI_PROVIDER": "  "})


def test_unknown_provider_is_rejected():
    with pytest.raises(AIConfigurationError):
        read_ai_settings({"AI_PROVIDER": "openai"})


def test_ollama_requires_explicit_model_tag():
    with pytest.raises(ProvidersNotConfigured, match="OLLAMA_MODEL"):
        load_generation({"AI_PROVIDER": "ollama"})


def test_ollama_settings_defaults_and_per_purpose_models():
    settings = read_ai_settings({**OLLAMA, "OLLAMA_MODEL_WEEKLY_REPORT": "qwen-big:32b"})
    assert settings.ollama.base_url == "http://localhost:11434"
    assert settings.ollama.models["analysis"] == "qwen-test:latest"
    assert settings.ollama.models["weekly_report"] == "qwen-big:32b"
    assert settings.ollama.format_mode == "schema" and settings.ollama.think is None
    assert settings.embedding.model == "bge-m3" and settings.embedding.dimensions == 1024
    generation, embedding = load_providers(OLLAMA)
    assert generation.identity.provider == "ollama" and generation.identity.mode == "live"
    assert embedding.identity.model == "bge-m3" and not is_external(generation)


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.0.10:11434",
        "https://localhost:11434",
        "http://example.com",
        "http://user:pw@localhost:11434",
        "http://localhost:11434/v1",
        "http://localhost.evil.com:11434",
        "http://127.0.0.2:11434",
    ],
)
def test_ollama_only_accepts_loopback_http(url):
    with pytest.raises(AIConfigurationError):
        loopback_url(url)


def test_loopback_variants_are_normalised():
    assert loopback_url("http://127.0.0.1") == "http://127.0.0.1:11434"
    assert loopback_url("http://[::1]:9999/") == "http://[::1]:9999"


def test_claude_requires_test_data_acknowledgement_and_key():
    without_ack = {k: v for k, v in CLAUDE.items() if k != "AI_CLAUDE_TEST_DATA_ONLY"}
    with pytest.raises(ProvidersNotConfigured, match="AI_CLAUDE_TEST_DATA_ONLY"):
        read_ai_settings(without_ack)
    with pytest.raises(ProvidersNotConfigured, match="AI_CLAUDE_TEST_DATA_ONLY"):
        read_ai_settings({**CLAUDE, "AI_CLAUDE_TEST_DATA_ONLY": "yes"})
    with pytest.raises(ProvidersNotConfigured, match="ANTHROPIC_API_KEY"):
        read_ai_settings({**CLAUDE, "ANTHROPIC_API_KEY": ""})


def test_claude_defaults_and_key_never_in_repr():
    settings = read_ai_settings({**CLAUDE, "CLAUDE_MODEL_SCAN": "claude-sonnet-5-5"})
    assert settings.claude.models["analysis"] == "claude-opus-5-5"
    assert settings.claude.models["scan"] == "claude-sonnet-5-5"
    assert settings.claude.effort == "low"
    assert "synthetic-not-a-real-key" not in repr(settings)
    # 임베딩은 Claude 설정이어도 로컬 Ollama다.
    assert settings.ollama.base_url == "http://localhost:11434"


@pytest.mark.parametrize(
    "override",
    [
        {"CLAUDE_EFFORT": "extreme"},
        {"CLAUDE_TIMEOUT_SECONDS": "0"},
        {"CLAUDE_MAX_RETRIES": "abc"},
        {"CLAUDE_MODEL": "bad model name"},
        {"EMBEDDING_DIMENSIONS": "5000"},
        {"OLLAMA_FORMAT": "xml"},
        {"OLLAMA_THINK": "maybe"},
    ],
)
def test_invalid_values_are_configuration_errors(override):
    with pytest.raises(AIConfigurationError) as error:
        read_ai_settings({**CLAUDE, **override})
    assert "synthetic-not-a-real-key" not in str(error.value)


def test_unknown_provider_objects_count_as_external():
    assert is_external(object())


def test_clean_json_text_only_strips_wrappers():
    assert clean_json_text('<think>생각</think>\n```json\n{"a": 1}\n```') == '{"a": 1}'
    assert clean_json_text(' {"a": 1} ') == '{"a": 1}'
    assert clean_json_text("not json") == "not json"


def test_strict_schema_closes_objects_and_drops_unsupported_constraints():
    schema = strict_schema(AnalysisResult.model_json_schema())
    text = str(schema)
    for key in ("maxLength", "minLength", "maxItems", "minimum", "'default'"):
        assert key not in text

    def objects(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                yield node
            for value in node.values():
                yield from objects(value)
        elif isinstance(node, list):
            for item in node:
                yield from objects(item)

    assert all(node["additionalProperties"] is False for node in objects(schema))
    # 원본은 바꾸지 않는다.
    assert "maxLength" in str(AnalysisResult.model_json_schema())
    # 필드 이름이 제약 이름과 같아도 지우지 않는다.
    named = strict_schema(
        {"type": "object", "properties": {"pattern": {"type": "string", "maxLength": 3}}}
    )
    assert named["properties"] == {"pattern": {"type": "string"}}
