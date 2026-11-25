"""지운 일정 다시 등록: 가짜 전송·가짜 저장소만 사용한다(DB·실제 Google 없음)."""

from types import SimpleNamespace

import pytest

from app.schemas.f5 import ExecutionReceipt
from app.services.calendar import CalendarStoredEvent, event_id
from app.services.f5 import F5Service
from app.services.f5_errors import CalendarError, F5Error

from .helpers import OWNER, SyntheticCalendarTransport, analysis, calendar, client, headers


class LiveTransport(SyntheticCalendarTransport):
    mode = "live"


def row(external_id, *, version=3, **overrides):
    payload = analysis().events[0].payload
    base = dict(
        type="calendar",
        status="approved",
        execution_status="succeeded",
        execution_mode="live",
        result=SimpleNamespace(external_id=external_id),
        version=version,
        payload=payload,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class Repository:
    def __init__(self, stored):
        self.stored, self.finished = stored, []

    def get(self, owner, suggestion_id):
        return self.stored

    def finish_reregister(self, owner, suggestion_id, version, receipt):
        self.finished.append((version, receipt))
        return receipt


def service_with(stored):
    adapter, transport = calendar(LiveTransport())
    repository = Repository(stored)
    return F5Service(repository, adapter), transport, repository


def put(transport, calendar_id, external_id, request_hash):
    transport.saved[(calendar_id, external_id)] = CalendarStoredEvent(external_id, request_hash)


def test_registered_is_true_only_while_the_event_is_alive():
    adapter, transport = calendar(LiveTransport())
    payload = analysis().events[0].payload
    old = event_id("sug-1")
    assert adapter.registered(OWNER, payload, old) is False  # 아예 없음
    put(transport, payload.calendar_id, old, "")  # 구글이 남겨 둔 '취소됨' 일정
    assert adapter.registered(OWNER, payload, old) is False
    put(transport, payload.calendar_id, old, "hash")
    assert adapter.registered(OWNER, payload, old) is True


def test_event_key_changes_event_id_and_is_idempotent():
    adapter, transport = calendar(LiveTransport())
    payload = analysis().events[0].payload
    first = adapter.execute(OWNER, "sug-1", payload)
    again = adapter.execute(OWNER, "sug-1", payload, event_key="sug-1:re3")
    assert first.external_id == event_id("sug-1") != again.external_id == event_id("sug-1:re3")
    adapter.execute(OWNER, "sug-1", payload, event_key="sug-1:re3")
    assert len(transport.writes) == 2  # 같은 키로 다시 보내도 새로 만들지 않는다


def test_reregister_recreates_deleted_event_with_a_new_id():
    stored = row(event_id("sug-1"))
    service, transport, repository = service_with(stored)
    payload = stored.payload
    put(transport, payload.calendar_id, event_id("sug-1"), "")  # 사용자가 캘린더에서 지움
    result = service.reregister(OWNER, "sug-1", 3)
    assert result.external_id == event_id("sug-1:re3") and result.mode == "live"
    assert len(transport.writes) == 1 and repository.finished[0][0] == 3
    assert isinstance(repository.finished[0][1], ExecutionReceipt)


def test_reregister_never_duplicates_a_live_event():
    stored = row(event_id("sug-1"))
    service, transport, repository = service_with(stored)
    put(transport, stored.payload.calendar_id, event_id("sug-1"), "hash")
    with pytest.raises(F5Error, match="calendar_event_exists"):
        service.reregister(OWNER, "sug-1", 3)
    assert transport.writes == [] and repository.finished == []


def test_reregister_second_time_checks_the_latest_event_id():
    # 한 번 다시 등록한 뒤(결과 ID가 새 ID) 또 지웠다면 한 번 더 새 ID로 만든다.
    stored = row(event_id("sug-1:re3"), version=5)
    service, transport, _ = service_with(stored)
    put(transport, stored.payload.calendar_id, event_id("sug-1:re3"), "")
    assert service.reregister(OWNER, "sug-1", 5).external_id == event_id("sug-1:re5")


@pytest.mark.parametrize(
    "overrides",
    [
        {"type": "todo"},
        {"status": "pending"},
        {"execution_status": "simulated"},
        {"execution_mode": "test"},
        {"result": None},
        {"result": SimpleNamespace(external_id=None)},
    ],
)
def test_reregister_only_for_really_registered_calendar_events(overrides):
    service, transport, repository = service_with(row(event_id("sug-1"), **overrides))
    with pytest.raises(F5Error, match="reregister_not_available"):
        service.reregister(OWNER, "sug-1", 3)
    assert transport.writes == [] and repository.finished == []


def test_reregister_rejects_stale_version_and_hides_provider_errors():
    service, transport, _ = service_with(row(event_id("sug-1")))
    with pytest.raises(F5Error, match="stale_version"):
        service.reregister(OWNER, "sug-1", 2)
    transport.failure = "permission"
    put(transport, service.repository.stored.payload.calendar_id, event_id("sug-1"), "")
    with pytest.raises(CalendarError) as error:
        service.reregister(OWNER, "sug-1", 3)
    assert error.value.code == "calendar_scope_required"


def test_reregister_route_passes_version_and_never_accepts_a_payload():
    seen = []

    class Stub:
        def reregister(self, owner, suggestion_id, version):
            seen.append((suggestion_id, version))
            raise F5Error("calendar_event_exists")

    http = client(Stub())
    response = http.post("/suggestions/sug-1/reregister", json={"version": 4}, headers=headers())
    assert response.status_code == 409 and seen == [("sug-1", 4)]
    assert response.json()["error"]["code"] == "calendar_event_exists"
    extra = http.post(
        "/suggestions/sug-1/reregister",
        json={"version": 4, "payload": {"title": "다른 내용"}},
        headers=headers(),
    )
    assert extra.status_code == 422 and seen == [("sug-1", 4)]
