"""F1 결과 → F5 제안 변환 검사용 합성 데이터와 대역. 실제 메일·제공자를 쓰지 않는다."""

import json
from collections import deque
from datetime import UTC, datetime

from app.ai.interfaces import ProviderIdentity
from app.schemas.f5 import ScanResult
from app.schemas.mail_analysis import AnalysisMail, AnalysisResult

from .helpers import BODY

MEETING = "📅 11월 20일 오후 2시에 테스트 회의를 합니다."
UPLOAD = "자료를 11월 19일까지 올려 주세요."
REPLY = "참석 가능 여부를 회신해 주세요."


def hint(kind, quote):
    start = BODY.index(quote)
    return {"kind": kind, "start": start, "end": start + len(quote)}


def f1_result(**overrides):
    value = {
        "mail_id": "f5-mail",
        "category": "meeting",
        "summary": "합성 회의 안내",
        "action_items": [{"text": "합성 자료 업로드", "due": "2026-11-19"}],
        "needs_reply": True,
        "priority": "normal",
        "priority_reason": "합성 회의 안내",
        "entities": {"projects": [], "orgs": [], "people": []},
        "events": [
            {
                "title": "합성 회의",
                "start": "2026-11-20T14:00:00+09:00",
                "end": "2026-11-20T15:00:00+09:00",
                "location": "테스트 회의실",
            }
        ],
        "evidence_spans": [hint("event", MEETING), hint("action", UPLOAD)],
    }
    value.update(overrides)
    return AnalysisResult.model_validate(value)


def links(events=None, todos=None, reply="default", mail_id="f5-mail"):
    return json.dumps(
        {
            "mail_id": mail_id,
            "events": [{"index": 0, "quote": MEETING}] if events is None else events,
            "action_items": [{"index": 0, "quote": UPLOAD}] if todos is None else todos,
            "reply": (
                {"reason": "참석 가능 여부 회신 요청", "quote": REPLY}
                if reply == "default"
                else reply
            ),
        },
        ensure_ascii=False,
    )


def analysis_mail(source="fixture"):
    return AnalysisMail.model_validate(
        {
            "mail_id": "f5-mail",
            "user_id": "f5-user",
            "account_id": "f5-account",
            "source": source,
            "thread_id": None,
            "received_at": datetime(2026, 11, 19, 1, tzinfo=UTC).isoformat(),
            "from_addr": "fixture@example.invalid",
            "from_name": "",
            "to": [],
            "cc": [],
            "subject": "합성 전용",
            "body_text": BODY,
        }
    )


class ScriptedScan:
    """정해 둔 응답을 차례로 돌려주는 테스트 대역(mode=test)."""

    identity = ProviderIdentity(provider="f5-test-double", model="scripted-scan", mode="test")

    def __init__(self, *responses, external=False):
        self.responses = deque(responses)
        self.calls = []
        self.external_transfer = external

    async def generate(self, request):
        self.calls.append(request)
        response = self.responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


class MemoryRepository:
    """DB 없이 서비스 경계를 확인하는 대역. ingest에 넘어온 후보만 기록한다."""

    def __init__(self, source="fixture"):
        self.source = source
        self.ingested = []

    def scan_source(self, owner, mail_id):
        return BODY, self.source

    def ingest(self, owner, analysis, candidates):
        self.ingested.append((owner, analysis, candidates))
        return ScanResult(items=[], created_ids=[f"sug_{i}" for i in range(len(candidates))])
