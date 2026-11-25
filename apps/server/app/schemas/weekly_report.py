"""F4 생성·저장·편집 계약. 첫 단위 ReportMail 계약은 변경하지 않는다."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from app.schemas.report import (
    Identifier,
    ReportMail,
    ReportModel,
    ReportPeriod,
    ReportScope,
    WeeklyReportInput,
)

ReportText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]
SectionName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ReportProfile(ReportModel):
    user_id: Identifier
    name: ReportText
    title: str = ""
    org: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    report_sections: tuple[SectionName, ...] = Field(min_length=1, max_length=20)
    report_recipient: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    report_style: Literal["bullet", "prose"]

    @model_validator(mode="after")
    def unique_sections(self) -> Self:
        if len(set(self.report_sections)) != len(self.report_sections):
            raise ValueError("보고 섹션 이름은 중복될 수 없습니다")
        return self


class ReportActor(ReportModel):
    user_id: Identifier
    sync_started_at: AwareDatetime
    account_id: Identifier | None = None


class GenerateWeeklyReport(ReportModel):
    ai_provider: Literal["default", "ollama", "claude"] | None = None
    start: date | None = None
    end: date | None = None
    template: Literal["profile", "bullet", "prose"] = "profile"
    recipient: ReportText | None = None
    regenerate: bool = False
    expected_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def complete_period(self) -> Self:
        if (self.start is None) != (self.end is None):
            raise ValueError("시작일과 종료일을 함께 선택하세요")
        if self.start is not None:
            ReportPeriod(start=self.start, end=self.end)
        return self


class GeneratedItem(ReportModel):
    text: ReportText
    evidence: tuple[Identifier, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_evidence(self) -> Self:
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError("근거 메일은 중복될 수 없습니다")
        return self


class GeneratedSection(ReportModel):
    name: SectionName
    items: tuple[GeneratedItem, ...] = Field(max_length=1000)


class GeneratedReport(ReportModel):
    sections: tuple[GeneratedSection, ...] = Field(min_length=1, max_length=20)


class ReportItem(GeneratedItem):
    item_id: Identifier


class ReportSection(ReportModel):
    name: SectionName
    items: tuple[ReportItem, ...] = Field(max_length=1000)


class EditWeeklyReport(ReportModel):
    expected_revision: int = Field(ge=1)
    sections: tuple[ReportSection, ...] = Field(min_length=1, max_length=20)


class WeeklyReportDocument(ReportModel):
    ai_execution: dict | None = None
    report_id: Identifier
    revision: int = Field(ge=1)
    period: ReportPeriod
    title: str
    subtitle: str
    recipient: str
    style: Literal["bullet", "prose"]
    sections: tuple[ReportSection, ...]
    scope: ReportScope
    evidence_mails: tuple[ReportMail, ...]
    status: Literal["ready", "empty"]
    generation: Literal["test_double", "ai", "none"]
    partial_period: bool = False
    collection_started_at: AwareDatetime | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class StoredWeeklyReport(ReportModel):
    user_id: Identifier
    account_id: Identifier | None = None
    selection_key: str
    profile: ReportProfile
    source: WeeklyReportInput
    document: WeeklyReportDocument


class WeeklyReportOptions(ReportModel):
    default_period: ReportPeriod
    profile: ReportProfile | None
    remaining_days: int = Field(ge=0)
    available_on: date
    generation: Literal["test_double", "ai", "unavailable"]
