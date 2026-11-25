"""SDK·공급자와 업무 로직 사이의 공통 계약."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    mode: Literal["live", "test"]


class ProvidersNotConfigured(RuntimeError):
    """제공자 없음은 분석 성공이나 메일별 분석 실패가 아니다."""


class ProviderCallError(RuntimeError):
    """어댑터는 외부 오류·키·본문을 이 예외 메시지로 전달하지 않는다.

    code는 고정 오류 코드(예: ollama_unreachable), 메시지는 고정된 한국어 안내다.
    """

    def __init__(
        self,
        message: str = "AI 호출에 실패했습니다",
        *,
        code: str = "provider_error",
        detail: str = "",
    ):
        super().__init__(message)
        self.code = code
        # 연결 검사 화면에만 보여 주는 제공자 안내(키 제거·길이 제한). 로그에는 쓰지 않는다.
        self.detail = detail


@dataclass(frozen=True, repr=False)
class GenerationRequest:
    purpose: Literal["analysis", "draft", "search", "weekly_report", "scan"]
    system_prompt: str
    user_prompt: str
    response_schema: dict


@dataclass(frozen=True, repr=False)
class EmbeddingRequest:
    texts: tuple[str, ...]
    purpose: Literal["document", "query"] = "document"


class TextGeneration(Protocol):
    identity: ProviderIdentity

    async def generate(self, request: GenerationRequest) -> str: ...


class TextEmbedding(Protocol):
    identity: ProviderIdentity
    dimensions: int

    async def embed(self, request: EmbeddingRequest) -> Sequence[Sequence[float]]: ...
