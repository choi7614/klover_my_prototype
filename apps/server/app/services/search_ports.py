"""F3 입출력 포트. F1의 공통 AI SDK/임베딩 구현을 대신 만들지 않는다."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.schemas.search import (
    AnswerDraft,
    ParsedQuery,
    ParseOutput,
    RankedHit,
    SearchMail,
    SearchScope,
    SemanticCoverage,
)


class ModelOutputInvalid(ValueError):
    """모델 응답이 재시도 후에도 계약 형식을 지키지 않았다. 응답 원문은 담지 않는다."""


class QueryParser(Protocol):
    async def parse(self, *, query: str, reference_date: date) -> ParseOutput:
        """메일 원문을 받지 않고 질의만 조건/주제로 나눈다. 날짜 기준은 한국 날짜다."""
        ...


class SearchAnswerer(Protocol):
    async def answer(
        self, *, query: str, parsed: ParsedQuery, mails: Sequence[SearchMail]
    ) -> AnswerDraft:
        """반환할 인용문과 mail_id는 전달된 검색 결과에서만 고른다."""
        ...


@dataclass(frozen=True)
class SemanticBatch:
    hits: tuple[RankedHit, ...]
    coverage: SemanticCoverage


class SemanticSearch(Protocol):
    @property
    def ready(self) -> bool:
        """로컬 제공자가 연결된 경우 참. 저장 범위의 호환성과 누락은 매 질의에 검사한다."""
        ...

    async def search(
        self, *, scope: SearchScope, parsed: ParsedQuery, limit: int
    ) -> Sequence[RankedHit] | SemanticBatch:
        """사용자·계정·시작 시점은 절대 완화하지 않는다. 조건은 동일하게 적용한다."""
        ...
