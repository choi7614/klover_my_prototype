"""F1 입력과 F5 전용 응답. 공유 생성 타입에는 아직 반영하지 않는다."""

from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]
Title = Annotated[str, Field(min_length=1, max_length=300, pattern=r"\S")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)


class Principal(Contract):
    user_id: Identifier
    account_id: Identifier


class EvidenceSpan(Contract):
    mail_id: Identifier
    start: Annotated[int, Field(ge=0, strict=True)]
    end: Annotated[int, Field(gt=0, strict=True)]
    quote: Annotated[str, Field(min_length=1, max_length=10000)]

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("근거 범위를 확인하세요")
        return self


class CalendarPayload(Contract):
    title: Title
    start: AwareDatetime
    end: AwareDatetime
    location: Annotated[str, Field(max_length=1000)] = ""
    calendar_id: Annotated[str | None, Field(min_length=1, max_length=256)] = None

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("일정 종료는 시작보다 늦어야 합니다")
        return self


class TodoPayload(Contract):
    title: Title
    due: date | None = None


class ReplyPayload(Contract):
    reason: Annotated[str, Field(min_length=1, max_length=1000, pattern=r"\S")]


class Candidate(Contract):
    action_key: Identifier
    evidence_spans: Annotated[list[EvidenceSpan], Field(min_length=1, max_length=20)]


class CalendarCandidate(Candidate):
    payload: CalendarPayload


class TodoCandidate(Candidate):
    payload: TodoPayload


class ReplyCandidate(Candidate):
    payload: ReplyPayload


class ScanInput(Contract):
    schema_version: Literal["f1.scan-input.v1"] = "f1.scan-input.v1"
    mail_id: Identifier
    body_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    offset_unit: Literal["unicode_codepoint"] = "unicode_codepoint"
    events: Annotated[list[CalendarCandidate], Field(max_length=50)] = Field(default_factory=list)
    action_items: Annotated[list[TodoCandidate], Field(max_length=50)] = Field(default_factory=list)
    reply: ReplyCandidate | None = None


class CalendarConflict(Contract):
    start: AwareDatetime
    end: AwareDatetime
    title: str | None = None

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("겹침 범위를 확인하세요")
        return self


class ConflictResult(Contract):
    status: Literal["checked", "unavailable"]
    conflicts: list[CalendarConflict] = Field(default_factory=list)
    request_hash: str
    error_code: str | None = None
    mode: Literal["test", "live", "none"] = "none"


class ExecutionReceipt(Contract):
    mode: Literal["test", "live", "internal"]
    external_id: str | None = None
    todo_id: str | None = None


class SuggestionView(Contract):
    suggestion_id: Identifier
    mail_id: Identifier
    type: Literal["calendar", "todo", "reply"]
    payload: CalendarPayload | TodoPayload | ReplyPayload
    evidence_spans: list[EvidenceSpan]
    body_sha256: str
    status: Literal["pending", "approved", "dismissed"]
    execution_status: Literal[
        "idle", "executing", "failed", "uncertain", "blocked", "simulated", "succeeded"
    ]
    execution_mode: Literal["none", "test", "live", "internal"]
    result: ExecutionReceipt | None = None
    last_error: str | None = None
    version: int
    notified_at: datetime | None
    created_at: datetime
    resolved_at: datetime | None

    @model_validator(mode="after")
    def real_approval_only(self) -> Self:
        if self.status == "approved" and (
            self.execution_status != "succeeded"
            or self.execution_mode not in {"live", "internal"}
            or self.result is None
            or self.result.mode != self.execution_mode
            or (
                self.type == "calendar"
                and (self.execution_mode != "live" or not self.result.external_id)
            )
            or (
                self.type == "todo"
                and (self.execution_mode != "internal" or not self.result.todo_id)
            )
        ):
            raise ValueError("실행 결과 없는 승인 상태는 허용하지 않습니다")
        return self


class SuggestionPage(Contract):
    items: list[SuggestionView]
    next_cursor: str | None = None


class ScanResult(Contract):
    items: list[SuggestionView]
    created_ids: list[str]


class ApproveRequest(Contract):
    version: Annotated[int, Field(ge=1, strict=True)]
    payload: dict[str, object] | None = None


class VersionRequest(Contract):
    version: Annotated[int, Field(ge=1, strict=True)]


class TodoCreate(TodoPayload):
    request_id: Identifier
    mail_id: Identifier | None = None


class TodoUpdate(Contract):
    version: Annotated[int, Field(ge=1, strict=True)]
    title: Title | None = None
    due: date | None = None
    status: Literal["open", "completed"] | None = None

    @model_validator(mode="after")
    def meaningful(self) -> Self:
        if not self.model_fields_set - {"version"}:
            raise ValueError("변경할 내용을 입력하세요")
        for key in ("title", "status"):
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError("빈 값으로 바꿀 수 없습니다")
        return self


class TodoView(Contract):
    todo_id: Identifier
    mail_id: Identifier | None
    suggestion_id: Identifier | None
    title: str
    due: date | None
    status: Literal["open", "completed"]
    version: int
    created_at: datetime
    updated_at: datetime


class TodoPage(Contract):
    items: list[TodoView]
    next_cursor: str | None = None


class SuggestionEvent(Contract):
    event_id: Identifier
    name: Literal["suggestion.created"] = "suggestion.created"
    schema_version: Literal["f5.notification.v1"] = "f5.notification.v1"
    suggestion_id: Identifier
    mail_id: Identifier
    type: Literal["calendar", "todo", "reply"]
    created_at: datetime


class EventPage(Contract):
    items: list[SuggestionEvent]
