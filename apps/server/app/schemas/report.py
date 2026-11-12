"""F4 보고 입력에 필요한 메일 조회 모델. DB 테이블·HTTP 응답 모델은 아니다."""

from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    model_validator,
)

REPORT_TIMEZONE = ZoneInfo("Asia/Seoul")
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
MailCategory = Literal[
    "work_request", "meeting", "approval", "report_share", "notice", "external", "newsletter"
]


class ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReportPeriod(ReportModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.end < self.start:
            raise ValueError("종료일은 시작일보다 빠를 수 없습니다")
        if self.end == date.max:
            raise ValueError("종료 다음 날의 조회 경계를 계산할 수 없습니다")
        return self

    @property
    def start_at(self) -> datetime:
        return datetime.combine(self.start, time.min, tzinfo=REPORT_TIMEZONE)

    @property
    def end_before(self) -> datetime:
        return datetime.combine(self.end + timedelta(days=1), time.min, tzinfo=REPORT_TIMEZONE)


class MailContact(ReportModel):
    addr: str
    name: str = ""
    org: str = ""


class MailEntities(ReportModel):
    projects: tuple[str, ...] = ()
    orgs: tuple[str, ...] = ()
    people: tuple[str, ...] = ()


class ReportMail(ReportModel):
    mail_id: Identifier
    user_id: Identifier
    thread_id: str | None = None
    direction: Literal["received", "sent"]
    received_at: AwareDatetime
    from_addr: str
    from_name: str = ""
    to: tuple[MailContact, ...]
    subject: str
    body_text: str
    analysis_status: Literal["pending", "done", "failed"]
    category: MailCategory | None = None
    user_label: MailCategory | None = None
    summary: str | None = None
    entities: MailEntities = Field(default_factory=MailEntities)

    @property
    def effective_category(self) -> MailCategory | None:
        return self.user_label if self.user_label is not None else self.category


class ReportMailGroup(ReportModel):
    group_id: str
    mails: tuple[ReportMail, ...] = Field(min_length=1)

    @computed_field
    @property
    def mail_ids(self) -> tuple[str, ...]:
        return tuple(mail.mail_id for mail in self.mails)


class ExcludedReportMail(ReportModel):
    mail: ReportMail
    reason: Literal["notice", "newsletter"]


class ReportScope(ReportModel):
    total: int
    grouped: int
    groups: int
    excluded: int


class WeeklyReportInput(ReportModel):
    period: ReportPeriod
    groups: tuple[ReportMailGroup, ...]
    excluded: tuple[ExcludedReportMail, ...]

    @computed_field
    @property
    def scope(self) -> ReportScope:
        grouped = sum(len(group.mails) for group in self.groups)
        excluded = len(self.excluded)
        return ReportScope(
            total=grouped + excluded,
            grouped=grouped,
            groups=len(self.groups),
            excluded=excluded,
        )
