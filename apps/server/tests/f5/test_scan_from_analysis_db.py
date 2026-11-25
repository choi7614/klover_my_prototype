"""실제 F5 저장소(분리 테스트 DB)에서 F1 결과 → 제안 저장·재실행·저장된 분석 읽기를 확인한다."""

import asyncio
import json

from sqlalchemy import text

from app.services.f5 import AnalysisScanHook

from .helpers import OTHER, OWNER
from .scan_support import ScriptedScan, analysis_mail, f1_result, links


def scan(f5db, generator, **options):
    return asyncio.run(
        f5db.service.scan_from_analysis(
            OWNER, "f5-mail", f1_result(), generator, allow_test_provider=True, **options
        )
    )


def test_creates_pending_suggestions_once_and_executes_nothing(f5db):
    first = scan(f5db, ScriptedScan(links()))
    assert first.status == "created" and len(first.result.created_ids) == 3
    items = f5db.service.repository.list(OWNER).items
    assert sorted(item.type for item in items) == ["calendar", "reply", "todo"]
    assert {item.status for item in items} == {"pending"}
    assert {item.execution_status for item in items} == {"idle"}
    assert f5db.transport.writes == []
    # 같은 메일 재분석(문구 변경)에도 같은 근거 위치면 새 제안·알림을 만들지 않는다.
    again = asyncio.run(
        f5db.service.scan_from_analysis(
            OWNER,
            "f5-mail",
            f1_result(action_items=[{"text": "자료 올리기", "due": "2026-11-19"}]),
            ScriptedScan(links()),
            allow_test_provider=True,
        )
    )
    assert again.status == "unchanged" and again.result.created_ids == []
    assert len(f5db.service.repository.events(OWNER).items) == 3


def test_hook_uses_trusted_mail_owner(f5db):
    hook = AnalysisScanHook(f5db.service, ScriptedScan(links()), allow_test_provider=True)
    outcome = asyncio.run(hook(analysis_mail(), f1_result()))
    assert (outcome.status, outcome.created) == ("created", 3)
    assert f5db.service.repository.list(OTHER).items == []


def test_other_owner_cannot_scan_mail(f5db):
    hook = AnalysisScanHook(f5db.service, ScriptedScan(links()), allow_test_provider=True)
    foreign = analysis_mail().model_copy(
        update={"user_id": OTHER.user_id, "account_id": OTHER.account_id}
    )
    outcome = asyncio.run(hook(foreign, f1_result()))
    assert (outcome.status, outcome.failure_code) == ("failed", "not_found")


def _store_f1_analysis(engine, *, status="done"):
    result = f1_result().model_dump(mode="json")
    with engine.begin() as connection:
        connection.execute(
            text("""
            CREATE TABLE f1_mail_analysis (
              mail_id text PRIMARY KEY, user_id text NOT NULL, account_id text NOT NULL,
              category text, user_label text, summary text, action_items jsonb NOT NULL,
              needs_reply boolean, priority text, priority_reason text, entities jsonb NOT NULL,
              events jsonb NOT NULL, evidence_spans jsonb NOT NULL, failure_code text)
        """)
        )
        connection.execute(
            text("""
            INSERT INTO f1_mail_analysis VALUES (:mail_id,:user_id,:account_id,:category,NULL,
              :summary,CAST(:action_items AS jsonb),:needs_reply,:priority,:priority_reason,
              CAST(:entities AS jsonb),CAST(:events AS jsonb),CAST(:evidence_spans AS jsonb),NULL)
        """),
            {
                **result,
                "user_id": OWNER.user_id,
                "account_id": OWNER.account_id,
                **{
                    key: json.dumps(result[key], ensure_ascii=False)
                    for key in ("action_items", "entities", "events", "evidence_spans")
                },
            },
        )
        connection.execute(
            text("UPDATE mails SET analysis_status=:status WHERE mail_id='f5-mail'"),
            {"status": status},
        )


def test_stored_analysis_reads_only_done_owned_results(f5db):
    repository = f5db.service.repository
    _store_f1_analysis(f5db.engine, status="pending")
    assert repository.stored_analysis(OWNER, "f5-mail") is None
    with f5db.engine.begin() as connection:
        connection.execute(text("UPDATE mails SET analysis_status='done' WHERE mail_id='f5-mail'"))
    stored = repository.stored_analysis(OWNER, "f5-mail")
    assert f1_result().model_validate(stored) == f1_result()
