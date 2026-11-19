import re

import pytest
from pydantic import ValidationError

from app.schemas.f5 import CalendarPayload
from app.services.calendar import (
    CalendarStoredEvent,
    CalendarTransportError,
    event_id,
    payload_hash,
)
from app.services.f5_errors import CalendarError

from .helpers import OTHER, OWNER, analysis, calendar


@pytest.mark.parametrize(
    "scopes",
    [
        [],
        ["https://www.googleapis.com/auth/gmail.readonly"],
        ["https://www.googleapis.com/auth/calendar.readonly"],
    ],
)
def test_console_enabled_or_readonly_never_grants_write(scopes):
    adapter, transport = calendar(scopes=scopes)
    with pytest.raises(CalendarError, match="calendar_scope_required"):
        adapter.execute(OWNER, "sug-1", analysis().events[0].payload)
    assert transport.writes == transport.finds == []


def test_owner_selection_and_timestamp_contracts():
    adapter, transport = calendar()
    payload = analysis().events[0].payload
    with pytest.raises(CalendarError, match="owner_mismatch"):
        adapter.execute(OTHER, "sug-1", payload)
    with pytest.raises(CalendarError, match="selection_required"):
        adapter.execute(OWNER, "sug-1", payload.model_copy(update={"calendar_id": None}))
    for overrides in [{"start": "2026-11-20T14:00:00"}, {"end": "2026-11-20T13:00:00+09:00"}]:
        with pytest.raises(ValidationError):
            CalendarPayload.model_validate(payload.model_dump(mode="json") | overrides)
    assert transport.writes == []
    assert re.fullmatch(r"[0-9a-v]{5,1024}", event_id("sug-1"))
    assert event_id("sug-1") != event_id("sug-2")
    assert payload_hash(payload) == payload_hash(
        CalendarPayload.model_validate(
            payload.model_dump(mode="json")
            | {"start": "2026-11-20T05:00:00Z", "end": "2026-11-20T06:00:00Z"}
        )
    )


def test_freebusy_reports_busy_without_invented_titles_and_no_writes():
    adapter, transport = calendar(scopes=["https://www.googleapis.com/auth/calendar.freebusy"])
    payload = analysis().events[0].payload
    result = adapter.conflicts(OWNER, payload)
    assert result.status == "checked" and result.mode == "test"
    assert len(result.conflicts) == 1 and result.conflicts[0].title is None
    transport.failure = "permission"
    assert adapter.conflicts(OWNER, payload).status == "unavailable"
    assert transport.writes == transport.finds == []


def test_events_write_scope_does_not_imply_freebusy_consent():
    adapter, transport = calendar()
    result = adapter.conflicts(OWNER, analysis().events[0].payload)
    assert result.status == "unavailable"
    assert transport.writes == []


def test_malformed_freebusy_is_unavailable_instead_of_false_no_conflict():
    adapter, transport = calendar(scopes=["https://www.googleapis.com/auth/calendar.freebusy"])
    transport.freebusy = lambda *args: [{"start": "bad-date", "end": "bad-date"}]
    result = adapter.conflicts(OWNER, analysis().events[0].payload)
    assert result.status == "unavailable"
    assert result.conflicts == [] and transport.writes == []


def test_conflict_and_receipt_identity_boundary():
    adapter, transport = calendar()
    payload = analysis().events[0].payload

    def race(request):
        transport.saved[(request.calendar_id, request.event_id)] = CalendarStoredEvent(
            request.event_id, request.request_hash
        )
        raise CalendarTransportError("conflict")

    transport.insert = race
    receipt = adapter.execute(OWNER, "sug-1", payload)
    assert receipt.mode == "test"
    transport.saved[(payload.calendar_id, event_id("sug-1"))] = CalendarStoredEvent(
        event_id("sug-1"), "wrong-hash"
    )
    with pytest.raises(CalendarError, match="execution_mismatch"):
        adapter.execute(OWNER, "sug-1", payload)
