"""F3 전용 계약. 소유자와 모델 선택은 요청에서 받지 않는다."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
MailID = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
Direction = Literal["received", "sent"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DateRange(Contract):
    start: date
    end_before: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end_before:
            raise ValueError("종료일은 시작일보다 뒤여야 합니다")
        return self


class RelativePeriod(Contract):
    relative: Literal["last_month", "this_week", "yesterday"]


class MonthPart(Contract):
    month: Annotated[int, Field(ge=1, le=12, strict=True)]
    part: Literal["early", "middle", "late"]
    year: Annotated[int, Field(ge=1900, le=9998, strict=True)] | None = None


class Counterparty(Contract):
    kind: Literal["name", "address", "organization"]
    value: Text


class SearchFilters(Contract):
    period: DateRange | None = None
    counterparty: Counterparty | None = None
    directions: Annotated[list[Direction], Field(min_length=1, max_length=2)] | None = None
    # 아직 없는 저장 정보를 조용히 무시하지 않기 위한 명시적 계약이다.
    needs_reply: bool | None = None
    replied: bool | None = None
    category: Text | None = None
    has_attachment: bool | None = None

    @model_validator(mode="after")
    def unique_directions(self):
        if self.directions and len(set(self.directions)) != len(self.directions):
            raise ValueError("대상 조건이 중복되었습니다")
        return self


class IntentFilters(SearchFilters):
    period: DateRange | RelativePeriod | MonthPart | None = None


class ParsedQuery(Contract):
    filters: SearchFilters = Field(default_factory=SearchFilters)
    topic: Text | None = None
    expansions: Annotated[list[Text], Field(max_length=8)] = Field(default_factory=list)
    original_terms: Annotated[list[Text], Field(max_length=4)] = Field(default_factory=list)

    @model_validator(mode="after")
    def expansions_require_topic(self):
        if self.topic is None and (self.expansions or self.original_terms):
            raise ValueError("주제 없이 확장어만 사용할 수 없습니다")
        return self


class ParseOutput(Contract):
    filters: IntentFilters
    topic: Text | None
    expansions: Annotated[list[Text], Field(max_length=8)] = Field(default_factory=list)
    original_terms: Annotated[list[Text], Field(max_length=4)] = Field(default_factory=list)

    @model_validator(mode="after")
    def meaningful(self):
        if self.topic is None and all(
            value is None for value in self.filters.model_dump().values()
        ):
            raise ValueError("질문에 대응하는 조건이나 주제가 필요합니다")
        return self


class SearchOverrides(SearchFilters):
    topic: Text | None = None


class SearchRequest(Contract):
    ai_provider: Literal["default", "ollama", "claude"] | None = None
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    overrides: SearchOverrides = Field(default_factory=SearchOverrides)
    search_id: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")] | None = None


class SearchScope(Contract):
    user_id: Text
    account_id: Text
    sync_started_at: AwareDatetime


class SearchMail(Contract):
    mail_id: MailID
    user_id: Text
    account_id: Text
    received_at: AwareDatetime
    history_imported: bool = False
    direction: Direction
    from_addr: str
    from_name: str = ""
    to: list[dict[str, str]] = Field(default_factory=list)
    subject: str
    body_text: str


class RankedHit(Contract):
    mail_id: MailID
    score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    excerpt: Annotated[str, Field(max_length=1200)] | None = None


class SearchResult(Contract):
    mail_id: MailID
    number: int
    score: float
    reason: str
    snippet: str
    match_terms: list[str]
    missing_conditions: list[str]
    sources: list[Literal["keyword", "metadata", "vector"]]
    subject: str
    from_name: str
    from_addr: str
    received_at: AwareDatetime
    direction: Direction


class EvidenceSentence(Contract):
    mail_id: MailID
    quote: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class AnswerDraft(Contract):
    # 자유 생성 문장의 사실성을 보장할 공통 모델이 없어, 검증 가능한 발췌만 받는다.
    sentences: Annotated[list[EvidenceSentence], Field(min_length=0, max_length=8)]


class Citation(Contract):
    number: int
    mail_id: MailID


class SearchAnswer(Contract):
    text: str
    sentences: list[EvidenceSentence]
    citations: list[Citation]


class SearchFailure(Contract):
    code: str
    message: str


class SemanticCoverage(Contract):
    eligible_mails: int = Field(ge=0)
    compatible_mails: int = Field(ge=0)
    scanned_chunks: int = Field(ge=0)
    limited: bool = False


class SearchResponse(Contract):
    ai_execution: dict | None = None
    search_id: str
    parsed: ParsedQuery
    reference_date: date
    results: list[SearchResult]
    partial: list[SearchResult]
    semantic_enabled: bool
    semantic_coverage: SemanticCoverage | None = None
    search_warnings: list[SearchFailure] = Field(default_factory=list)
    truncated: bool
    answer: SearchAnswer | None = None
    answer_error: SearchFailure | None = None


class RecentSearch(Contract):
    search_id: str
    query: str
    created_at: datetime


class StoredSearch(Contract):
    search_id: str
    query: str
    parsed: ParsedQuery
    overrides: SearchOverrides
    reference_date: date
