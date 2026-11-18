"""실제 제공자 연결 지점. 미설정 상태에서 테스트 대역으로 대체하지 않는다."""

from app.ai.interfaces import ProvidersNotConfigured, TextEmbedding, TextGeneration


def load_providers() -> tuple[TextGeneration, TextEmbedding]:
    raise ProvidersNotConfigured("실제 AI·임베딩 제공자가 아직 연결되지 않았습니다")
