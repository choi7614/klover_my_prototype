"""실제 계정·메일·HTTP transport가 없는 합성 데이터와 테스트 앱."""

import hashlib
from datetime import UTC, datetime
from threading import Event
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_error_handlers
from app.api.f5 import register_f5_api
from app.api.mail_read import MailAPIContext
from app.schemas.f5 import CalendarConflict, Principal, ScanInput
from app.services.calendar import (
    CalendarGrant,
    CalendarStoredEvent,
    CalendarTransportError,
    GoogleCalendarAdapter,
)

OWNER = Principal(user_id="f5-user", account_id="f5-account")
OTHER = Principal(user_id="other-user", account_id="other-account")
BODY = (
    "합성 메일입니다.\n"
    "📅 11월 20일 오후 2시에 테스트 회의를 합니다.\n"
    "자료를 11월 19일까지 올려 주세요.\n"
    "참석 가능 여부를 회신해 주세요."
)
TOKEN = "f5-synthetic-token-" + "A" * 43
START = datetime(2026, 11, 19, tzinfo=UTC)


def span(quote, mail_id="f5-mail"):
    start = BODY.index(quote)
    return {"mail_id": mail_id, "start": start, "end": start + len(quote), "quote": quote}


def analysis():
    return ScanInput.model_validate(
        {
            "mail_id": "f5-mail",
            "body_sha256": hashlib.sha256(BODY.encode()).hexdigest(),
            "events": [
                {
                    "action_key": "meeting-1",
                    "evidence_spans": [span("📅 11월 20일 오후 2시에 테스트 회의를 합니다.")],
                    "payload": {
                        "title": "합성 회의",
                        "start": "2026-11-20T14:00:00+09:00",
                        "end": "2026-11-20T15:00:00+09:00",
                        "location": "테스트 회의실",
                        "calendar_id": "synthetic-calendar",
                    },
                }
            ],
            "action_items": [
                {
                    "action_key": "upload-1",
                    "evidence_spans": [span("자료를 11월 19일까지 올려 주세요.")],
                    "payload": {"title": "합성 자료 업로드", "due": "2026-11-19"},
                }
            ],
            "reply": {
                "action_key": "reply-1",
                "evidence_spans": [span("참석 가능 여부를 회신해 주세요.")],
                "payload": {"reason": "참석 가능 여부 회신"},
            },
        }
    )


class SyntheticCalendarTransport:
    mode = "test"

    def __init__(self):
        self.saved = {}
        self.writes = []
        self.finds = []
        self.failure = None
        self.entered, self.release = Event(), Event()
        self.pause = False

    def find(self, calendar_id, event_id):
        self.finds.append((calendar_id, event_id))
        if self.failure == "find_timeout":
            raise CalendarTransportError("timeout")
        return self.saved.get((calendar_id, event_id))

    def insert(self, request):
        self.entered.set()
        if self.pause:
            assert self.release.wait(timeout=10)
        if self.failure == "permission":
            raise CalendarTransportError("permission")
        self.writes.append(request)
        stored = CalendarStoredEvent(request.event_id, request.request_hash)
        self.saved[(request.calendar_id, request.event_id)] = stored
        if self.failure == "timeout_after_store":
            raise CalendarTransportError("timeout")
        return stored

    def freebusy(self, calendar_id, payload):
        if self.failure:
            raise CalendarTransportError("permission")
        return [CalendarConflict(start=payload.start, end=payload.end)]


def calendar(transport=None, scopes=None, owner=OWNER):
    transport = transport or SyntheticCalendarTransport()
    return GoogleCalendarAdapter(
        CalendarGrant(
            owner,
            frozenset(
                scopes
                if scopes is not None
                else ["https://www.googleapis.com/auth/calendar.events"]
            ),
        ),
        transport,
    ), transport


def client(service, owner=OWNER):
    app = FastAPI()
    register_error_handlers(app)
    register_f5_api(app, service)
    app.state.mail_api = MailAPIContext(TOKEN, SimpleNamespace(session=lambda: owner))
    return TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 12345))


def headers():
    return {"Authorization": "Bearer " + TOKEN}
