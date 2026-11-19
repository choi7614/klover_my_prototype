"""F3 입출력 포트. F1의 공통 AI SDK/임베딩 구현을 대신 만들지 않는다."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from app.schemas.search import (
    AnswerDraft,
    ParsedQuery,
    ParseOutput,
    RankedHit,
    SearchMail,
    SearchScope,
)


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


class SemanticSearch(Protocol):
    @property
    def ready(self) -> bool:
        """실제 제공자와 저장 벡터의 provider/model/차원/mode가 일치하고 준비된 경우만 참."""
        ...

    async def search(
        self, *, scope: SearchScope, parsed: ParsedQuery, limit: int
    ) -> Sequence[RankedHit]:
        """사용자·계정·시작 시점은 절대 완화하지 않는다. 조건은 동일하게 적용한다."""
        ...
