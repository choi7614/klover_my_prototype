"""F1 분석 결과 → F5 제안 변환에 쓰는 AI 응답·결과 모델. 공유 생성 타입에는 넣지 않는다."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.f5 import ScanResult

Quote = Annotated[str, Field(min_length=1, max_length=2000)]


class ScanModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class LinkedItem(ScanModel):
    """AI가 돌려주는 '몇 번 항목의 근거는 이 문장' 연결. 내용(제목·일시)은 F1 결과를 쓴다."""

    index: int = Field(ge=0, le=99, strict=True)
    quote: Quote


class ReplyLink(ScanModel):
    reason: Annotated[str, Field(min_length=1, max_length=300)]
    quote: Quote


class ScanLinks(ScanModel):
    mail_id: Annotated[str, Field(min_length=1, max_length=128)]
    events: Annotated[list[LinkedItem], Field(max_length=50)]
    action_items: Annotated[list[LinkedItem], Field(max_length=50)]
    reply: ReplyLink | None


SkipReason = Literal[
    # F1 결과에 일정 종료 시각이 없다. 임의로 만들지 않는다.
    "event_end_unknown",
    # 제목이 제안 제목 한도(300자)를 넘는다.
    "title_too_long",
    # AI가 근거 문장을 주지 않았다.
    "evidence_missing",
    # AI가 준 근거 문장이 원문에 그대로 없다.
    "evidence_not_found",
    # 같은 유형의 다른 제안이 이미 같은 근거 위치를 쓴다.
    "duplicate_evidence",
]


class SkippedItem(ScanModel):
    type: Literal["calendar", "todo", "reply"]
    index: int | None
    reason: SkipReason


class AnalysisScanResult(ScanModel):
    """제안 생성 결과. 메일 본문·근거 문장은 담지 않는 요약(items는 저장된 제안)."""

    status: Literal["created", "unchanged", "nothing_to_suggest"]
    result: ScanResult
    skipped: tuple[SkippedItem, ...] = ()
    attempts: int = 0


class AnalysisScanOutcome(ScanModel):
    """F1 완료 알림 지점에 돌려줄 결과.

    실패해도 F1 분석 저장을 되돌리지 않도록 예외 대신 반환한다.
    """

    mail_id: str
    status: Literal["created", "unchanged", "nothing_to_suggest", "failed"]
    created: int = 0
    skipped: int = 0
    failure_code: str | None = None
