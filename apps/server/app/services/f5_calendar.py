"""현재 계정·소유 캘린더를 매번 검증한 뒤 기존 F5 실행 경계를 사용한다."""

from app.connectors.google_calendar import GoogleCalendarHTTP
from app.schemas.f5 import ConflictResult
from app.services.calendar import (
    CalendarGrant,
    CalendarTransportError,
    GoogleCalendarAdapter,
    payload_hash,
)
from app.services.f5_errors import CalendarError


class ConnectedCalendar:
    def __init__(self, repository, settings, transport=None):
        self.repository, self.settings, self.transport = repository, settings, transport

    def connection(self, owner):
        email = self.repository.email(owner)
        try:
            tokens = self.repository.refresh(owner, self.settings, self.transport)
            http = GoogleCalendarHTTP(tokens["access_token"], self.transport)
            calendars = http.calendars()
            return {"status": "connected", "email": email, "calendars": calendars}, tokens, http
        except (CalendarTransportError, ValueError, KeyError, TypeError, AttributeError) as error:
            code = {
                "auth": "calendar_permission_expired",
                "permission": "calendar_scope_required",
            }.get(getattr(error, "kind", "unavailable"), "calendar_connection_failed")
            raise CalendarError(code, blocked=True) from None

    def status(self, owner):
        try:
            return self.connection(owner)[0]
        except CalendarError as error:
            return {"status": error.code, "email": self.repository.email(owner), "calendars": []}

    def _adapter(self, owner, payload):
        state, tokens, http = self.connection(owner)
        if payload.calendar_id not in {x["id"] for x in state["calendars"]}:
            raise CalendarError("calendar_selection_required", blocked=True)
        return GoogleCalendarAdapter(CalendarGrant(owner, frozenset(tokens["scope"].split())), http)

    def execute(self, owner, suggestion_id, payload, event_key=None):
        return self._adapter(owner, payload).execute(owner, suggestion_id, payload, event_key)

    def registered(self, owner, payload, external_id):
        return self._adapter(owner, payload).registered(owner, payload, external_id)

    def conflicts(self, owner, payload):
        try:
            return self._adapter(owner, payload).conflicts(owner, payload)
        except CalendarError as error:
            return ConflictResult(
                status="unavailable", request_hash=payload_hash(payload), error_code=error.code
            )
