"""F1 분석 결과 → F5 입력 변환과 근거 검증. DB 없이 실행된다(대역 제공자·저장소)."""

import asyncio
import json

import pytest

from app.ai.interfaces import ProvidersNotConfigured
from app.cli import f5_scan
from app.pipeline.scan_analysis import ScanFailed, action_key, body_sha256, build_scan_input
from app.services.f5 import AnalysisScanHook, F5Service

from .helpers import BODY, OWNER
from .scan_support import (
    MEETING,
    REPLY,
    UPLOAD,
    MemoryRepository,
    ScriptedScan,
    analysis_mail,
    f1_result,
    links,
)


def build(result, generator):
    return asyncio.run(build_scan_input("f5-mail", BODY, result, generator, timeout=5))


def test_converts_f1_result_with_exact_evidence_and_payload_from_f1():
    llm = ScriptedScan(links())
    built = build(f1_result(), llm)
    value = built.scan_input
    assert built.attempts == 1 and built.skipped == ()
    assert value.body_sha256 == body_sha256(BODY)
    event, todo, reply = value.events[0], value.action_items[0], value.reply
    # 내용은 F1 결과 그대로, 근거는 원문 위치(코드 포인트)와 정확히 일치한다.
    assert event.payload.title == "합성 회의" and event.payload.location == "테스트 회의실"
    assert todo.payload.title == "합성 자료 업로드" and str(todo.payload.due) == "2026-11-19"
    assert reply.payload.reason == "참석 가능 여부 회신 요청"
    for candidate, quote in ((event, MEETING), (todo, UPLOAD), (reply, REPLY)):
        span = candidate.evidence_spans[0]
        assert BODY[span.start : span.end] == span.quote == quote
    # 이모지가 있어도 Python 문자열(코드 포인트) 위치다.
    assert event.evidence_spans[0].start == BODY.index(MEETING)
    assert event.action_key == action_key(
        "calendar", BODY.index(MEETING), BODY.index(MEETING) + len(MEETING)
    )
    # AI 호출은 scan 목적의 공통 TextGeneration 한 번이다.
    request = llm.calls[0]
    assert request.purpose == "scan" and "근거" in request.system_prompt
    sent = json.loads(request.user_prompt)
    assert sent["mail_id"] == "f5-mail" and sent["needs_reply"] is True


def test_action_key_is_stable_across_reanalysis_wording():
    first = build(f1_result(), ScriptedScan(links())).scan_input
    reworded = f1_result(action_items=[{"text": "자료 올리기", "due": "2026-11-19"}])
    second = build(reworded, ScriptedScan(links())).scan_input
    assert first.action_items[0].action_key == second.action_items[0].action_key


def test_nothing_to_suggest_does_not_call_ai():
    result = f1_result(events=[], action_items=[], needs_reply=False, evidence_spans=[])
    built = build(result, None)
    assert not built.has_candidates and built.attempts == 0


def test_missing_provider_is_reported_when_ai_needed():
    with pytest.raises(ScanFailed) as error:
        build(f1_result(), None)
    assert error.value.code == "provider_not_configured"


def test_event_without_end_is_skipped_not_invented():
    result = f1_result(
        events=[
            {
                "title": "합성 회의",
                "start": "2026-11-20T14:00:00+09:00",
                "end": None,
                "location": None,
            }
        ]
    )
    llm = ScriptedScan(links(events=[]))
    built = build(result, llm)
    assert built.scan_input.events == []
    assert [(s.type, s.reason) for s in built.skipped] == [("calendar", "event_end_unknown")]
    assert json.loads(llm.calls[0].user_prompt)["events"] == []


def test_fenced_or_think_wrapped_json_is_accepted():
    raw = "<think>생각</think>\n```json\n" + links() + "\n```"
    built = build(f1_result(), ScriptedScan(raw))
    assert built.has_candidates and built.attempts == 1


@pytest.mark.parametrize(
    "bad",
    [
        "형식이 아닌 응답",
        links(mail_id="other-mail"),
        links(todos=[{"index": 7, "quote": UPLOAD}]),
        links(todos=[{"index": 0, "quote": UPLOAD}, {"index": 0, "quote": UPLOAD}]),
        json.dumps({"mail_id": "f5-mail", "events": [], "action_items": [], "reply": None, "x": 1}),
    ],
)
def test_format_violation_retries_once_then_succeeds(bad):
    llm = ScriptedScan(bad, links())
    built = build(f1_result(), llm)
    assert built.attempts == 2 and built.has_candidates
    assert json.loads(llm.calls[1].user_prompt)["retry_reason"] == "invalid_response"


def test_format_violation_twice_fails_without_suggestions():
    llm = ScriptedScan("아님", "{}")
    with pytest.raises(ScanFailed) as error:
        build(f1_result(), llm)
    assert (error.value.code, error.value.attempts) == ("invalid_response", 2)


def test_reply_when_f1_says_no_reply_is_invalid():
    result = f1_result(needs_reply=False)
    llm = ScriptedScan(links(), links(reply=None))
    built = build(result, llm)
    assert built.attempts == 2 and built.scan_input.reply is None


def test_paraphrased_quote_is_retried_then_dropped():
    paraphrased = links(todos=[{"index": 0, "quote": "자료를 19일까지 올려주세요"}])
    llm = ScriptedScan(paraphrased, paraphrased)
    built = build(f1_result(), llm)
    assert built.attempts == 2
    assert json.loads(llm.calls[1].user_prompt)["retry_reason"] == "evidence_not_found"
    # 원문에 없는 근거로는 제안을 만들지 않고, 나머지는 그대로 만든다.
    assert built.scan_input.action_items == []
    assert len(built.scan_input.events) == 1 and built.scan_input.reply is not None
    assert [(s.type, s.reason) for s in built.skipped] == [("todo", "evidence_not_found")]


def test_omitted_item_is_retried_then_reported():
    llm = ScriptedScan(links(events=[]), links(events=[]))
    built = build(f1_result(), llm)
    assert [(s.type, s.reason) for s in built.skipped] == [("calendar", "evidence_missing")]


def test_quote_whitespace_trim_and_duplicate_evidence_are_handled():
    result = f1_result(
        action_items=[
            {"text": "합성 자료 업로드", "due": "2026-11-19"},
            {"text": "같은 문장 다른 할 일", "due": None},
        ]
    )
    same = [{"index": 0, "quote": "  " + UPLOAD + "\n"}, {"index": 1, "quote": UPLOAD}]
    built = build(result, ScriptedScan(links(todos=same), links(todos=same)))
    assert len(built.scan_input.action_items) == 1
    assert built.scan_input.action_items[0].evidence_spans[0].quote == UPLOAD
    assert [(s.index, s.reason) for s in built.skipped] == [(1, "duplicate_evidence")]


def test_provider_error_and_timeout_are_fixed_codes():
    with pytest.raises(ScanFailed) as error:
        build(f1_result(), ScriptedScan(RuntimeError("비밀 응답 원문")))
    assert error.value.code == "provider_error" and "비밀" not in str(error.value)

    class Slow(ScriptedScan):
        async def generate(self, request):
            await asyncio.sleep(1)

    with pytest.raises(ScanFailed) as error:
        asyncio.run(build_scan_input("f5-mail", BODY, f1_result(), Slow(), timeout=0.01))
    assert error.value.code == "timeout"


def test_analysis_for_other_mail_or_other_body_is_rejected():
    with pytest.raises(ScanFailed):
        asyncio.run(build_scan_input("other", BODY, f1_result(), ScriptedScan(links())))
    with pytest.raises(ScanFailed):
        asyncio.run(build_scan_input("f5-mail", "짧음", f1_result(), ScriptedScan(links())))


def test_service_stores_only_and_blocks_test_provider_by_default():
    repository = MemoryRepository()
    service = F5Service(repository)
    with pytest.raises(ProvidersNotConfigured):
        asyncio.run(
            service.scan_from_analysis(OWNER, "f5-mail", f1_result(), ScriptedScan(links()))
        )
    assert repository.ingested == []
    outcome = asyncio.run(
        service.scan_from_analysis(
            OWNER, "f5-mail", f1_result(), ScriptedScan(links()), allow_test_provider=True
        )
    )
    assert outcome.status == "created" and len(outcome.result.created_ids) == 3
    kinds = [kind for kind, _ in repository.ingested[0][2]]
    assert kinds == ["calendar", "todo", "reply"]
    # 기본 실행기는 차단 상태 그대로다. 생성만으로 어떤 실행도 하지 않는다.
    assert type(service.calendar).__name__ == "BlockedCalendar"


@pytest.mark.parametrize(("allow", "external"), [(False, False), (True, True), (False, True)])
def test_gmail_content_requires_explicit_allow_and_local_provider(allow, external):
    service = F5Service(MemoryRepository(source="gmail"))
    llm = ScriptedScan(links(), external=external)
    with pytest.raises(ScanFailed) as error:
        asyncio.run(
            service.scan_from_analysis(
                OWNER, "f5-mail", f1_result(), llm, allow_gmail=allow, allow_test_provider=True
            )
        )
    assert error.value.code == "external_transfer_blocked" and llm.calls == []


def test_gmail_content_with_local_provider_and_allow_flag():
    service = F5Service(MemoryRepository(source="gmail"))
    outcome = asyncio.run(
        service.scan_from_analysis(
            OWNER,
            "f5-mail",
            f1_result(),
            ScriptedScan(links()),
            allow_gmail=True,
            allow_test_provider=True,
        )
    )
    assert outcome.status == "created"


def test_hook_returns_outcome_and_never_raises():
    repository = MemoryRepository()
    hook = AnalysisScanHook(F5Service(repository), ScriptedScan(links()), allow_test_provider=True)
    outcome = asyncio.run(hook(analysis_mail(), f1_result()))
    assert (outcome.status, outcome.created, outcome.failure_code) == ("created", 3, None)
    assert repository.ingested[0][0] == OWNER

    failing = AnalysisScanHook(
        F5Service(MemoryRepository()), ScriptedScan("x", "y"), allow_test_provider=True
    )
    outcome = asyncio.run(failing(analysis_mail(), f1_result()))
    assert (outcome.status, outcome.failure_code) == ("failed", "invalid_response")

    unconfigured = AnalysisScanHook(F5Service(MemoryRepository()), None)
    outcome = asyncio.run(unconfigured(analysis_mail(), f1_result()))
    assert (outcome.status, outcome.failure_code) == ("failed", "provider_not_configured")


def test_cli_without_provider_stops_before_db(monkeypatch, capsys):
    monkeypatch.setenv("AI_PROVIDER", "")
    called = []
    monkeypatch.setattr(f5_scan, "database_engine", lambda: called.append(1))
    code = f5_scan.main(["--user-id", "u", "--account-id", "a", "--mail-id", "m"])
    output = json.loads(capsys.readouterr().out)
    assert code == 1 and output["status"] == "not_configured" and called == []
