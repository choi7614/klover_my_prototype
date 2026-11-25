"""실제 제공자 연결 지점. .env의 AI_PROVIDER로 Claude 또는 로컬 Ollama(Qwen 등)를 고른다.

- AI_PROVIDER가 비어 있으면 지금처럼 미연결(ProvidersNotConfigured)이다.
- 어느 경우에도 테스트 대역이나 가짜 결과로 대체하지 않는다.
- 임베딩은 제공자와 관계없이 이 컴퓨터의 Ollama(bge-m3 기본)를 쓴다.
"""

from collections.abc import Mapping

from app.ai.config import AISettings, read_ai_settings
from app.ai.interfaces import ProvidersNotConfigured, TextEmbedding, TextGeneration

NOT_CONFIGURED = "실제 AI 제공자가 설정되지 않았습니다 (.env의 AI_PROVIDER)"


def _settings(values: Mapping[str, str | None] | None) -> AISettings:
    settings = read_ai_settings(values)
    if settings.provider is None:
        raise ProvidersNotConfigured(NOT_CONFIGURED)
    return settings


def load_generation(values: Mapping[str, str | None] | None = None) -> TextGeneration:
    settings = _settings(values)
    if settings.provider == "claude":
        # 앱에서 저장한 로컬 전용 정책은 환경 변수 기반 CLI에서도 우회하지 않는다.
        from app.ai.selection import AISettingsStore

        store = AISettingsStore()
        if (store.directory / "ai-settings.enc").exists() and store.read().get(
            "mode", "hybrid"
        ) == "local_only":
            raise ProvidersNotConfigured("로컬 전용 모드에서는 Claude 호출을 차단합니다.")
    if settings.provider == "claude":
        from app.ai.claude import ClaudeGeneration

        return ClaudeGeneration(settings.claude)
    from app.ai.ollama import OllamaGeneration

    return OllamaGeneration(settings.ollama)


def load_embedding(values: Mapping[str, str | None] | None = None) -> TextEmbedding:
    settings = _settings(values)
    from app.ai.ollama import OllamaEmbedding

    return OllamaEmbedding(settings.embedding, settings.ollama.base_url)


def load_providers(
    values: Mapping[str, str | None] | None = None,
) -> tuple[TextGeneration, TextEmbedding]:
    # 설정을 한 번만 읽어 두 제공자가 같은 값을 보게 한다.
    from app.ai.config import environment_values

    values = environment_values() if values is None else values
    return load_generation(values), load_embedding(values)


def is_external(provider: object) -> bool:
    """외부 서버로 내용을 보내는 제공자인지. 알 수 없으면 외부로 간주한다."""
    return getattr(provider, "external_transfer", True) is not False
