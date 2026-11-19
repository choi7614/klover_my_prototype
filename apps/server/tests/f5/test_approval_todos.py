from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.repositories.f5_schema import Todo
from app.schemas.f5 import ApproveRequest, TodoCreate, TodoUpdate
from app.services.f5 import F5Service
from app.services.f5_errors import F5Error

from .helpers import OTHER, OWNER


def calendar_suggestion(f5db):
    return f5db.service.scan(OWNER, f5db.analysis).items[0]


def test_missing_calendar_and_reply_never_become_approved(f5db):
    rows = f5db.service.scan(OWNER, f5db.analysis).items
    blocked = F5Service(f5db.repository)
    for row in (rows[0], rows[2]):
        with pytest.raises(F5Error) as caught:
            blocked.approve(OWNER, row.suggestion_id, ApproveRequest(version=row.version))
        assert caught.value.status == 503
        result = f5db.repository.get(OWNER, row.suggestion_id)
        assert result.status == "pending" and result.execution_status == "blocked"
        assert result.result is None
    assert f5db.transport.writes == []


def test_edited_approval_is_simulated_and_duplicate_uses_same_event_id(f5db):
    row = calendar_suggestion(f5db)
    payload = row.payload.model_dump(mode="json") | {
        "title": "사용자가 수정한 합성 제목",
        "location": "바꾼 테스트 장소",
    }
    result = f5db.service.approve(
        OWNER, row.suggestion_id, ApproveRequest(version=row.version, payload=payload)
    )
    assert result.status == "pending" and result.execution_status == "simulated"
    assert result.execution_mode == result.result.mode == "test"
    assert f5db.transport.writes[0].payload.title == payload["title"]
    repeated = f5db.service.approve(
        OWNER, row.suggestion_id, ApproveRequest(version=result.version)
    )
    assert repeated.result.external_id == result.result.external_id
    assert len(f5db.transport.writes) == 1
    assert len(f5db.repository.events(OWNER).items) == 3


def test_concurrent_calendar_approval_executes_once(f5db):
    row = calendar_suggestion(f5db)
    f5db.transport.pause = True
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            f5db.service.approve, OWNER, row.suggestion_id, ApproveRequest(version=row.version)
        )
        assert f5db.transport.entered.wait(timeout=5)
        try:
            # 서로 다른 서비스/연결도 DB에 저장한 실행 권한을 공유해야 한다.
            second_service = F5Service(f5db.repository, f5db.service.calendar)
            with pytest.raises(F5Error, match="execution_in_progress"):
                second_service.approve(
                    OWNER, row.suggestion_id, ApproveRequest(version=row.version)
                )
            with pytest.raises(F5Error, match="cannot_dismiss"):
                f5db.repository.dismiss(OWNER, row.suggestion_id, row.version)
        finally:
            f5db.transport.release.set()
        assert first.result(timeout=5).execution_status == "simulated"
    assert len(f5db.transport.writes) == 1


def test_timeout_after_remote_write_freezes_payload_and_reconciles(f5db):
    row = calendar_suggestion(f5db)
    f5db.transport.failure = "timeout_after_store"
    with pytest.raises(F5Error, match="calendar_result_unknown"):
        f5db.service.approve(OWNER, row.suggestion_id, ApproveRequest(version=row.version))
    unknown = f5db.repository.get(OWNER, row.suggestion_id)
    assert unknown.status == "pending" and unknown.execution_status == "uncertain"
    assert unknown.result is None
    with pytest.raises(F5Error, match="uncertain_payload_locked"):
        f5db.service.approve(
            OWNER,
            row.suggestion_id,
            ApproveRequest(
                version=unknown.version,
                payload=unknown.payload.model_dump(mode="json") | {"title": "다른 요청"},
            ),
        )
    with pytest.raises(F5Error, match="cannot_dismiss"):
        f5db.repository.dismiss(OWNER, row.suggestion_id, unknown.version)
    f5db.transport.failure = None
    reconciled = f5db.service.approve(
        OWNER, row.suggestion_id, ApproveRequest(version=unknown.version)
    )
    assert reconciled.execution_status == "simulated" and reconciled.status == "pending"
    assert len(f5db.transport.writes) == 1


def test_failed_reconciliation_preserves_uncertainty_and_calendar_lock(f5db):
    row = calendar_suggestion(f5db)
    f5db.transport.failure = "timeout_after_store"
    with pytest.raises(F5Error, match="calendar_result_unknown"):
        f5db.service.approve(OWNER, row.suggestion_id, ApproveRequest(version=1))
    current = f5db.repository.get(OWNER, row.suggestion_id)
    original_find = f5db.transport.find

    def no_permission(*args):
        from app.services.calendar import CalendarTransportError

        raise CalendarTransportError("permission")

    f5db.transport.find = no_permission
    with pytest.raises(F5Error, match="calendar_scope_required"):
        f5db.service.approve(OWNER, row.suggestion_id, ApproveRequest(version=current.version))
    current = f5db.repository.get(OWNER, row.suggestion_id)
    assert current.execution_status == "uncertain" and current.status == "pending"
    with pytest.raises(F5Error, match="uncertain_payload_locked"):
        f5db.service.approve(
            OWNER,
            row.suggestion_id,
            ApproveRequest(
                version=current.version,
                payload=current.payload.model_dump(mode="json")
                | {"calendar_id": "different-calendar"},
            ),
        )
    f5db.transport.find = original_find
    f5db.transport.failure = None
    f5db.service.approve(OWNER, row.suggestion_id, ApproveRequest(version=current.version))
    assert len(f5db.transport.writes) == 1


def test_definite_failure_invalid_payload_and_wrong_user(f5db):
    row = calendar_suggestion(f5db)
    for owner, body, code in [
        (OTHER, ApproveRequest(version=1), "not_found"),
        (OWNER, ApproveRequest(version=1, payload={"title": "불완전한 일정"}), "invalid_payload"),
        (OWNER, ApproveRequest(version=2), "stale_version"),
    ]:
        with pytest.raises(F5Error, match=code):
            f5db.service.approve(owner, row.suggestion_id, body)
    assert f5db.transport.writes == []
    f5db.transport.failure = "permission"
    with pytest.raises(F5Error, match="calendar_scope_required"):
        f5db.service.approve(OWNER, row.suggestion_id, ApproveRequest(version=1))
    failed = f5db.repository.get(OWNER, row.suggestion_id)
    assert failed.status == "pending" and failed.execution_status == "blocked"
    f5db.transport.failure = None
    assert (
        f5db.service.approve(
            OWNER, row.suggestion_id, ApproveRequest(version=failed.version)
        ).execution_status
        == "simulated"
    )


def test_todo_approval_is_atomic_repeated_and_concurrent(f5db):
    row = next(r for r in f5db.service.scan(OWNER, f5db.analysis).items if r.type == "todo")
    body = ApproveRequest(
        version=row.version, payload={"title": "수정한 할 일", "due": "2026-11-21"}
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: f5db.service.approve(OWNER, row.suggestion_id, body), range(4))
        )
    assert all(r.status == "approved" and r.execution_mode == "internal" for r in results)
    assert len({r.result.todo_id for r in results}) == 1
    with Session(f5db.engine) as session:
        assert session.scalar(select(func.count()).select_from(Todo)) == 1
    todo = f5db.repository.list_todos(OWNER).items[0]
    assert todo.title == "수정한 할 일" and todo.suggestion_id == row.suggestion_id
    assert todo.mail_id == row.mail_id and todo.due.isoformat() == "2026-11-21"
    assert row.suggestion_id not in {e.suggestion_id for e in f5db.repository.events(OWNER).items}
    with pytest.raises(F5Error, match="already_approved_with_other_payload"):
        f5db.service.approve(
            OWNER, row.suggestion_id, ApproveRequest(version=1, payload={"title": "또 바꾼 할 일"})
        )


def test_direct_todo_idempotency_and_update_ownership(f5db):
    body = TodoCreate(
        request_id="test-request", mail_id="f5-mail", title="직접 만든 합성 할 일", due="2026-11-22"
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda _: f5db.repository.create_todo(OWNER, body), range(3)))
    assert len({r.todo_id for r in rows}) == 1
    todo = rows[0]
    with pytest.raises(F5Error, match="request_id_reused"):
        f5db.repository.create_todo(OWNER, body.model_copy(update={"title": "다른 작업"}))
    with pytest.raises(F5Error, match="not_found"):
        f5db.repository.update_todo(OTHER, todo.todo_id, TodoUpdate(version=1, status="completed"))
    changed = f5db.repository.update_todo(
        OWNER,
        todo.todo_id,
        TodoUpdate(version=1, title="수정한 제목", due=None, status="completed"),
    )
    assert changed.due is None and changed.status == "completed" and changed.version == 2
    with pytest.raises(F5Error, match="stale_version"):
        f5db.repository.update_todo(OWNER, todo.todo_id, TodoUpdate(version=1, status="open"))
    assert f5db.repository.list_todos(OTHER).items == []
    assert f5db.repository.list_todos(OWNER, status="open").items == []


def test_process_interruption_does_not_release_execution_claim(f5db):
    row = calendar_suggestion(f5db)
    claimed, token = f5db.repository.claim(
        OWNER, row.suggestion_id, 1, row.payload.model_dump(mode="json")
    )
    f5db.service.calendar.execute(OWNER, row.suggestion_id, row.payload)
    # 외부 실행 후 DB 확정 전 중단한 상황을 모사한다. 다른 프로세스의 자동 재실행은 거부한다.
    with pytest.raises(F5Error, match="execution_in_progress"):
        f5db.service.approve(OWNER, row.suggestion_id, ApproveRequest(version=claimed.version))
    assert len(f5db.transport.writes) == 1
    with pytest.raises(F5Error, match="execution_claim_lost"):
        f5db.repository.finish(OWNER, row.suggestion_id, "wrong-token", receipt=None)
    assert f5db.repository.get(OWNER, row.suggestion_id).status == "pending"
    assert token is not None
