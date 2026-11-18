"""F1 분석 계약. 기존 F4 분류 코드와 연결하고 AI 응답을 엄격히 검사한다."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.report import MailCategory, MailContact

Text = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]


class AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class AnalysisEntities(AnalysisModel):
    projects: tuple[Text, ...]
    orgs: tuple[Text, ...]
    people: tuple[Text, ...]


class ActionItem(AnalysisModel):
    text: Text
    due: date | None

    @field_validator("due", mode="before")
    @classmethod
    def iso_date(cls, value):
        if value is None or type(value) is date:
            return value
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError("마감 날짜는 YYYY-MM-DD여야 합니다")
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("마감 날짜는 YYYY-MM-DD여야 합니다")
        return parsed


class CalendarEvent(AnalysisModel):
    title: Text
    start: AwareDatetime
    end: AwareDatetime | None
    location: Text | None

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end is not None and self.end <= self.start:
            raise ValueError("일정 종료는 시작보다 늦어야 합니다")
        return self


class EvidenceSpan(AnalysisModel):
    kind: Literal["action", "due", "event"]
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("근거 범위가 비어 있습니다")
        return self


class AnalysisResult(AnalysisModel):
    mail_id: Text
    category: MailCategory
    summary: Text = Field(max_length=1000)
    action_items: tuple[ActionItem, ...] = Field(max_length=100)
    needs_reply: bool = Field(strict=True)
    priority: Literal["high", "normal", "low"]
    priority_reason: Text = Field(max_length=500)
    entities: AnalysisEntities
    events: tuple[CalendarEvent, ...] = Field(max_length=100)
    evidence_spans: tuple[EvidenceSpan, ...] = Field(max_length=200)

    @field_validator("summary")
    @classmethod
    def short_summary(cls, value):
        if len(value.splitlines()) > 2:
            raise ValueError("요약은 1~2줄이어야 합니다")
        return value

    def check_source(self, mail: "AnalysisMail") -> None:
        if self.mail_id != mail.mail_id:
            raise ValueError("분석 대상 메일이 다릅니다")
        if any(span.end > len(mail.body_text) for span in self.evidence_spans):
            raise ValueError("근거가 원문 범위를 벗어납니다")


class AnalysisMail(AnalysisModel):
    mail_id: Text
    user_id: Text
    account_id: Text
    source: Literal["fixture", "gmail"]
    thread_id: str | None
    received_at: AwareDatetime
    from_addr: Text
    from_name: str
    to: tuple[MailContact, ...]
    cc: tuple[MailContact, ...]
    subject: str
    body_text: str


class CategoryExample(AnalysisModel):
    subject: str
    category: MailCategory


class AnalysisOutcome(AnalysisModel):
    mail_id: str
    status: Literal["done", "failed"]
    failure_code: str | None = None
    attempts: int


class CategoryUpdate(AnalysisModel):
    category: MailCategory


class CategoryUpdated(AnalysisModel):
    mail_id: str
    user_label: MailCategory
    effective_category: MailCategory
