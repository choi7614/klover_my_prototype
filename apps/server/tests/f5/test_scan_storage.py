from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Mail
from app.db.repositories.f5 import F5Repository
from app.db.repositories.f5_schema import Dismissal, Outbox, Suggestion
from app.schemas.f5 import ScanInput
from app.services.f5_errors import F5Error

from .helpers import OWNER


def test_scan_reanalysis_persistence_no_execution_and_single_event(f5db):
    result = f5db.service.scan(OWNER, f5db.analysis)
    assert len(result.items) == len(result.created_ids) == 3
    assert {r.type for r in result.items} == {"calendar", "todo", "reply"}
    assert all(r.status == "pending" and r.execution_status == "idle" for r in result.items)
    assert f5db.transport.writes == f5db.transport.finds == []
    incoming = f5db.analysis.model_dump(mode="json")
    incoming["events"][0]["action_key"] = "changed-f1-key"
    incoming["events"][0]["payload"]["title"] = "재분석으로 바꾼 제목"
    again = f5db.service.scan(OWNER, ScanInput.model_validate(incoming))
    assert again.created_ids == []
    assert again.items[0].payload.title == "합성 회의"
    f5db.engine.dispose()
    repo = F5Repository(f5db.engine)
    assert len(repo.list(OWNER).items) == len(repo.events(OWNER).items) == 3
    assert repo.get(OWNER, result.items[0].suggestion_id).mail_id == "f5-mail"


def test_concurrent_scans_create_one_set(f5db):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: f5db.service.scan(OWNER, f5db.analysis), range(4)))
    assert sum(len(r.created_ids) for r in results) == 3
    assert len(f5db.repository.events(OWNER).items) == 3


@pytest.mark.parametrize("case", ["mail", "span-mail", "range", "quote", "hash", "unicode"])
def test_invalid_evidence_rejected_atomically(f5db, case):
    incoming = f5db.analysis.model_dump(mode="json")
    evidence = incoming["action_items"][0]["evidence_spans"][0]
    if case == "mail":
        incoming["mail_id"] = "foreign-mail"
    elif case == "span-mail":
        evidence["mail_id"] = "foreign-mail"
    elif case == "range":
        evidence["end"] = 100000
    elif case == "quote":
        evidence["quote"] = "본문에 없는 합성 문장"
    elif case == "hash":
        incoming["body_sha256"] = "0" * 64
    else:
        # 이모지 뒤 UTF-16 위치를 보내면 코드 포인트 기준 검증을 통과할 수 없다.
        evidence["start"] += 1
        evidence["end"] += 1
    with pytest.raises(F5Error):
        f5db.service.scan(OWNER, ScanInput.model_validate(incoming))
    assert f5db.repository.list(OWNER).items == []
    assert f5db.repository.events(OWNER).items == []


def test_dismissal_survives_retry_no_renotification_and_ack_is_explicit(f5db):
    items = f5db.service.scan(OWNER, f5db.analysis).items
    first = items[0]
    assert len(f5db.repository.list(OWNER, status="pending", notified=False).items) == 3
    f5db.repository.events(OWNER)
    assert f5db.repository.get(OWNER, first.suggestion_id).notified_at is None
    event = next(
        e for e in f5db.repository.events(OWNER).items if e.suggestion_id == first.suggestion_id
    )
    f5db.repository.ack_event(OWNER, event.event_id)
    f5db.repository.ack_event(OWNER, event.event_id)
    assert f5db.repository.get(OWNER, first.suggestion_id).notified_at is not None
    dismissed = f5db.repository.dismiss(OWNER, first.suggestion_id, first.version)
    assert dismissed.status == "dismissed" and dismissed.resolved_at is not None
    assert f5db.repository.dismiss(OWNER, first.suggestion_id, first.version) == dismissed
    f5db.service.scan(OWNER, f5db.analysis)
    assert len(f5db.repository.list(OWNER, status="pending", notified=False).items) == 2
    assert len(f5db.repository.events(OWNER).items) == 2
    with Session(f5db.engine) as session:
        assert session.scalar(select(func.count()).select_from(Dismissal)) == 1
        assert session.scalar(select(func.count()).select_from(Outbox)) == 3


def test_ownership_fk_and_current_source_validation(f5db):
    row = f5db.service.scan(OWNER, f5db.analysis).items[0]
    for action in [
        lambda: f5db.repository.get(f5db.other, row.suggestion_id),
        lambda: f5db.repository.dismiss(f5db.other, row.suggestion_id, row.version),
    ]:
        with pytest.raises(F5Error) as caught:
            action()
        assert caught.value.status == 404
    with Session(f5db.engine) as session, pytest.raises(IntegrityError):
        session.execute(update(Suggestion).values(user_id=f5db.other.user_id))
        session.commit()
    with Session(f5db.engine) as session, session.begin():
        session.execute(
            update(Mail).where(Mail.mail_id == row.mail_id).values(body_text="바뀐 합성 본문")
        )
    with pytest.raises(F5Error, match="stale_source"):
        f5db.repository.get(OWNER, row.suggestion_id)


def test_stable_page_and_bad_cursor(f5db):
    f5db.service.scan(OWNER, f5db.analysis)
    cursor, ids = None, []
    for _ in range(3):
        page = f5db.repository.list(OWNER, limit=1, cursor=cursor)
        ids += [r.suggestion_id for r in page.items]
        cursor = page.next_cursor
    assert len(set(ids)) == 3 and cursor is None
    with pytest.raises(F5Error, match="invalid_cursor"):
        f5db.repository.list(OWNER, cursor="invalid!")
