"""Google Calendar 실행 경계. 실제 HTTP·토큰 접근·동의 변경은 제공하지 않는다."""

import hashlib
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import ValidationError

from app.schemas.f5 import (
    CalendarConflict,
    CalendarPayload,
    ConflictResult,
    ExecutionReceipt,
    Principal,
)
from app.services.f5_errors import CalendarError

WRITE_SCOPES = frozenset(
    {"https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/calendar"}
)
BUSY_SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.freebusy",
        "https://www.googleapis.com/auth/calendar.events.freebusy",
    }
)


def payload_hash(payload: CalendarPayload) -> str:
    # 같은 시각의 다른 오프셋 표현도 같은 실행 요청으로 취급한다.
    from datetime import UTC

    canonical = payload.model_copy(
        update={"start": payload.start.astimezone(UTC), "end": payload.end.astimezone(UTC)}
    )
    return hashlib.sha256(canonical.model_dump_json().encode()).hexdigest()


def event_id(suggestion_id: str) -> str:
    # Google event.id가 허용하는 base32hex 문자 집합의 부분집합이다.
    return hashlib.sha256(("klover-f5:" + suggestion_id).encode()).hexdigest()


@dataclass(frozen=True)
class CalendarGrant:
    owner: Principal
    scopes: frozenset[str]


@dataclass(frozen=True)
class CalendarWrite:
    calendar_id: str
    event_id: str
    payload: CalendarPayload
    request_hash: str


@dataclass(frozen=True)
class CalendarStoredEvent:
    event_id: str
    request_hash: str


class CalendarTransportError(Exception):
    """transport는 원문 대신 고정 오류 종류로 변환해야 한다."""

    def __init__(self, kind: Literal["auth", "permission", "unavailable", "timeout", "conflict"]):
        self.kind = (
            kind
            if kind in {"auth", "permission", "unavailable", "timeout", "conflict"}
            else "unavailable"
        )
        super().__init__(self.kind)


class CalendarTransport(Protocol):
    mode: Literal["test", "live"]

    def find(self, calendar_id: str, event_id: str) -> CalendarStoredEvent | None: ...

    def insert(self, request: CalendarWrite) -> CalendarStoredEvent: ...

    def freebusy(self, calendar_id: str, payload: CalendarPayload) -> list[CalendarConflict]: ...


class CalendarAdapter(Protocol):
    def execute(
        self, owner: Principal, suggestion_id: str, payload: CalendarPayload
    ) -> ExecutionReceipt: ...

    def conflicts(self, owner: Principal, payload: CalendarPayload) -> ConflictResult: ...


class BlockedCalendar:
    def execute(self, owner, suggestion_id, payload):
        raise CalendarError("calendar_not_connected", blocked=True)

    def conflicts(self, owner, payload):
        return ConflictResult(
            status="unavailable",
            request_hash=payload_hash(payload),
            error_code="calendar_not_connected",
        )


class GoogleCalendarAdapter:
    def __init__(self, grant: CalendarGrant, transport: CalendarTransport):
        self.grant, self.transport = grant, transport

    def _check(self, owner, payload, scopes):
        if owner != self.grant.owner:
            raise CalendarError("calendar_owner_mismatch", blocked=True)
        if not self.grant.scopes & scopes:
            raise CalendarError("calendar_scope_required", blocked=True)
        if not payload.calendar_id:
            raise CalendarError("calendar_selection_required", blocked=True)

    def _receipt(self, stored, request):
        if stored.event_id != request.event_id or stored.request_hash != request.request_hash:
            raise CalendarError("calendar_execution_mismatch", uncertain=True)
        return ExecutionReceipt(mode=self.transport.mode, external_id=stored.event_id)

    def execute(self, owner, suggestion_id, payload):
        self._check(owner, payload, WRITE_SCOPES)
        request = CalendarWrite(
            payload.calendar_id, event_id(suggestion_id), payload, payload_hash(payload)
        )
        inserting = False
        try:
            existing = self.transport.find(request.calendar_id, request.event_id)
            if existing:
                return self._receipt(existing, request)
            inserting = True
            return self._receipt(self.transport.insert(request), request)
        except CalendarTransportError as error:
            if error.kind == "conflict" and inserting:
                try:
                    existing = self.transport.find(request.calendar_id, request.event_id)
                except CalendarTransportError:
                    raise CalendarError("calendar_result_unknown", uncertain=True) from None
                if existing:
                    return self._receipt(existing, request)
                raise CalendarError("calendar_result_unknown", uncertain=True) from None
            if error.kind in {"auth", "permission"}:
                raise CalendarError("calendar_scope_required", blocked=True) from None
            # find 실패는 쓰기 전, insert 타임아웃은 이미 등록됐을 수도 있다.
            uncertain = inserting and error.kind in {"timeout", "unavailable"}
            raise CalendarError(
                "calendar_result_unknown" if uncertain else "calendar_unavailable",
                uncertain=uncertain,
            ) from None

    def conflicts(self, owner, payload):
        try:
            self._check(owner, payload, BUSY_SCOPES)
            rows = self.transport.freebusy(payload.calendar_id, payload)
            validated = [CalendarConflict.model_validate(row) for row in rows]
            conflicts = [
                row for row in validated if row.start < payload.end and row.end > payload.start
            ]
            return ConflictResult(
                status="checked",
                conflicts=conflicts,
                request_hash=payload_hash(payload),
                mode=self.transport.mode,
            )
        except (CalendarError, CalendarTransportError, ValidationError, TypeError):
            return ConflictResult(
                status="unavailable",
                request_hash=payload_hash(payload),
                error_code="calendar_freebusy_unavailable",
                mode=self.transport.mode,
            )
