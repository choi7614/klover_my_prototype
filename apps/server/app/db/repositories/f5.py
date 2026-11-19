"""F5 저장소. 모든 조회·상태 전이를 소유 사용자·계정으로 제한한다."""

import base64
import hashlib
import json
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import and_, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Mail, MailAccount
from app.db.repositories.f5_schema import Dismissal, Outbox, Suggestion, Todo
from app.schemas.f5 import (
    EventPage,
    ExecutionReceipt,
    ScanResult,
    SuggestionEvent,
    SuggestionPage,
    SuggestionView,
    TodoPage,
    TodoView,
)
from app.services.f5_errors import F5Error


def now():
    return datetime.now(UTC)


def identifier(prefix):
    return prefix + "_" + uuid4().hex


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _encode_cursor(row, key):
    raw = json.dumps([row.created_at.isoformat(), getattr(row, key)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value):
    try:
        if len(value) > 512:
            raise ValueError
        fields = json.loads(
            base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        )
        if not isinstance(fields, list) or len(fields) != 2:
            raise ValueError
        timestamp = datetime.fromisoformat(fields[0])
        if (
            timestamp.tzinfo is None
            or not isinstance(fields[1], str)
            or not 1 <= len(fields[1]) <= 128
        ):
            raise ValueError
        return timestamp, fields[1]
    except (ValueError, TypeError, OverflowError):
        raise F5Error("invalid_cursor", 422) from None


class F5Repository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def _owned(model, owner):
        return select(model).where(
            model.user_id == owner.user_id, model.account_id == owner.account_id
        )

    def _mail(self, session, owner, mail_id, *, lock=False):
        query = (
            self._owned(Mail, owner)
            .join(MailAccount, MailAccount.account_id == Mail.account_id)
            .where(
                Mail.mail_id == mail_id,
                Mail.direction == "received",
                Mail.received_at >= MailAccount.sync_started_at,
            )
        )
        row = session.scalar(query.with_for_update(of=Mail) if lock else query)
        if row is None:
            raise F5Error("not_found", 404)
        return row

    def _suggestion(self, session, owner, suggestion_id, *, lock=False):
        query = self._owned(Suggestion, owner).where(Suggestion.suggestion_id == suggestion_id)
        row = session.scalar(query.with_for_update() if lock else query)
        if row is None:
            raise F5Error("not_found", 404)
        # DB의 복합 FK와 별개로 현재 원본의 소유권도 확인한다.
        mail = self._mail(session, owner, row.mail_id)
        if hashlib.sha256(mail.body_text.encode()).hexdigest() != row.body_sha256:
            raise F5Error("stale_source")
        return row

    def scan_source(self, owner, mail_id):
        """제안 생성에 쓸 원본 본문과 메일 출처(fixture/gmail). 소유·수신 시작 시점을 확인한다."""
        with Session(self.engine) as session:
            mail = self._mail(session, owner, mail_id)
            source = session.scalar(
                select(MailAccount.source).where(
                    MailAccount.account_id == owner.account_id,
                    MailAccount.user_id == owner.user_id,
                )
            )
            return mail.body_text, source

    def stored_analysis(self, owner, mail_id):
        """F1이 저장한 성공 분석 결과(읽기 전용). 없거나 실패·대기 중이면 None."""
        with Session(self.engine) as session:
            self._mail(session, owner, mail_id)
            if session.scalar(text("SELECT to_regclass('f1_mail_analysis')")) is None:
                raise F5Error("analysis_storage_unavailable", 503)
            row = (
                session.execute(
                    text("""
                    SELECT a.mail_id, a.category, a.summary, a.action_items, a.needs_reply,
                           a.priority, a.priority_reason, a.entities, a.events, a.evidence_spans
                    FROM f1_mail_analysis a JOIN mails m
                      ON m.mail_id=a.mail_id AND m.user_id=a.user_id AND m.account_id=a.account_id
                    WHERE a.mail_id=:mail_id AND a.user_id=:user_id AND a.account_id=:account_id
                      AND a.failure_code IS NULL AND a.category IS NOT NULL
                      AND m.analysis_status='done'
                """),
                    {
                        "mail_id": mail_id,
                        "user_id": owner.user_id,
                        "account_id": owner.account_id,
                    },
                )
                .mappings()
                .first()
            )
            return None if row is None else dict(row)

    def ingest(self, owner, analysis, candidates):
        created, rows = [], []
        with Session(self.engine) as session, session.begin():
            mail = self._mail(session, owner, analysis.mail_id, lock=True)
            if hashlib.sha256(mail.body_text.encode()).hexdigest() != analysis.body_sha256:
                raise F5Error("stale_analysis", 422)
            for kind, candidate in candidates:
                for span in candidate.evidence_spans:
                    if (
                        span.mail_id != mail.mail_id
                        or span.end > len(mail.body_text)
                        or mail.body_text[span.start : span.end] != span.quote
                        or not span.quote.strip()
                    ):
                        raise F5Error("invalid_evidence", 422)
                spans = sorted(
                    [s.model_dump() for s in candidate.evidence_spans],
                    key=lambda item: (item["start"], item["end"]),
                )
                evidence_key = digest(spans)
                matching = list(
                    session.scalars(
                        select(Suggestion).where(
                            Suggestion.mail_id == mail.mail_id,
                            Suggestion.type == kind,
                            or_(
                                Suggestion.action_key == candidate.action_key,
                                Suggestion.evidence_key == evidence_key,
                            ),
                        )
                    )
                )
                if len(matching) > 1:
                    raise F5Error("analysis_identity_conflict", 422)
                if matching:
                    row = matching[0]
                    if row.body_sha256 != analysis.body_sha256:
                        raise F5Error("source_revision_requires_review")
                else:
                    row = Suggestion(
                        suggestion_id=identifier("sug"),
                        user_id=owner.user_id,
                        account_id=owner.account_id,
                        mail_id=mail.mail_id,
                        type=kind,
                        action_key=candidate.action_key,
                        evidence_key=evidence_key,
                        body_sha256=analysis.body_sha256,
                        payload=candidate.payload.model_dump(mode="json"),
                        evidence_spans=spans,
                        created_at=now(),
                    )
                    session.add(row)
                    session.flush()
                    session.add(
                        Outbox(
                            event_id="evt_" + digest([row.suggestion_id, "suggestion.created"]),
                            suggestion_id=row.suggestion_id,
                            user_id=owner.user_id,
                            account_id=owner.account_id,
                            created_at=row.created_at,
                        )
                    )
                    created.append(row.suggestion_id)
                if row.suggestion_id not in {r.suggestion_id for r in rows}:
                    rows.append(row)
            return ScanResult(
                items=[SuggestionView.model_validate(r) for r in rows], created_ids=created
            )

    def get(self, owner, suggestion_id):
        with Session(self.engine) as session:
            return SuggestionView.model_validate(self._suggestion(session, owner, suggestion_id))

    def list(self, owner, *, status=None, mail_id=None, notified=None, limit=20, cursor=None):
        with Session(self.engine) as session:
            query = self._owned(Suggestion, owner)
            if status is not None:
                query = query.where(Suggestion.status == status)
            if mail_id is not None:
                self._mail(session, owner, mail_id)
                query = query.where(Suggestion.mail_id == mail_id)
            if notified is not None:
                query = query.where(
                    Suggestion.notified_at.is_not(None)
                    if notified
                    else Suggestion.notified_at.is_(None)
                )
            rows, next_cursor = self._page(
                session, query, Suggestion, "suggestion_id", limit, cursor
            )
            return SuggestionPage(
                items=[SuggestionView.model_validate(r) for r in rows], next_cursor=next_cursor
            )

    @staticmethod
    def _page(session, query, model, key, limit, cursor):
        if not 1 <= limit <= 100:
            raise F5Error("invalid_limit", 422)
        column = getattr(model, key)
        if cursor:
            stamp, value = _decode_cursor(cursor)
            query = query.where(
                or_(model.created_at > stamp, and_(model.created_at == stamp, column > value))
            )
        rows = list(session.scalars(query.order_by(model.created_at, column).limit(limit + 1)))
        return rows[:limit], _encode_cursor(rows[limit - 1], key) if len(rows) > limit else None

    @staticmethod
    def _ready(row, version, payload):
        if row.status == "approved":
            if row.execution_payload != payload:
                raise F5Error("already_approved_with_other_payload")
            return False
        if row.status != "pending":
            raise F5Error("suggestion_dismissed")
        if row.execution_status == "executing":
            raise F5Error("execution_in_progress")
        if row.version != version:
            raise F5Error("stale_version")
        if row.execution_status == "uncertain" and row.execution_payload != payload:
            raise F5Error("uncertain_payload_locked")
        return True

    def claim(self, owner, suggestion_id, version, payload):
        with Session(self.engine) as session, session.begin():
            row = self._suggestion(session, owner, suggestion_id, lock=True)
            if not self._ready(row, version, payload):
                return SuggestionView.model_validate(row), None
            token = identifier("attempt")
            row.execution_token = token
            row.execution_payload = payload
            row.payload = payload
            row.execution_status = "executing"
            row.execution_mode = "none"
            row.result = None
            row.last_error = None
            row.started_at = now()
            row.version += 1
            session.flush()
            return SuggestionView.model_validate(row), token

    def finish(self, owner, suggestion_id, token, *, receipt=None, error=None):
        with Session(self.engine) as session, session.begin():
            row = self._suggestion(session, owner, suggestion_id, lock=True)
            if row.execution_token != token or row.execution_status != "executing":
                raise F5Error("execution_claim_lost")
            if error:
                row.last_error = error.code
                row.execution_status = (
                    "uncertain" if error.uncertain else "blocked" if error.blocked else "failed"
                )
                row.execution_mode = "none"
            else:
                row.result = receipt.model_dump(mode="json")
                row.execution_mode = receipt.mode
                row.execution_status = "simulated" if receipt.mode == "test" else "succeeded"
                if receipt.mode != "test":
                    row.status, row.resolved_at = "approved", now()
            row.execution_token = None
            row.version += 1
            session.flush()
            return SuggestionView.model_validate(row)

    def approve_todo(self, owner, suggestion_id, version, payload):
        with Session(self.engine) as session, session.begin():
            row = self._suggestion(session, owner, suggestion_id, lock=True)
            if row.type != "todo":
                raise F5Error("invalid_suggestion_type", 422)
            if self._ready(row, version, payload):
                stamp = now()
                todo = Todo(
                    todo_id=identifier("todo"),
                    user_id=owner.user_id,
                    account_id=owner.account_id,
                    mail_id=row.mail_id,
                    suggestion_id=row.suggestion_id,
                    title=payload["title"],
                    due=date.fromisoformat(payload["due"]) if payload.get("due") else None,
                    created_at=stamp,
                    updated_at=stamp,
                )
                session.add(todo)
                session.flush()
                row.payload = payload
                row.execution_payload = payload
                row.result = ExecutionReceipt(mode="internal", todo_id=todo.todo_id).model_dump(
                    mode="json"
                )
                row.status, row.execution_status, row.execution_mode = (
                    "approved",
                    "succeeded",
                    "internal",
                )
                row.resolved_at, row.last_error = stamp, None
                row.version += 1
                session.flush()
            return SuggestionView.model_validate(row)

    def dismiss(self, owner, suggestion_id, version):
        with Session(self.engine) as session, session.begin():
            row = self._suggestion(session, owner, suggestion_id, lock=True)
            if row.status == "dismissed":
                return SuggestionView.model_validate(row)
            if row.status != "pending" or row.execution_status in {"executing", "uncertain"}:
                raise F5Error("cannot_dismiss")
            if row.version != version:
                raise F5Error("stale_version")
            row.status, row.resolved_at = "dismissed", now()
            row.version += 1
            session.add(
                Dismissal(
                    suggestion_id=row.suggestion_id,
                    user_id=owner.user_id,
                    account_id=owner.account_id,
                    dismissed_at=row.resolved_at,
                )
            )
            session.flush()
            return SuggestionView.model_validate(row)

    def create_todo(self, owner, request):
        payload = request.model_dump(mode="json", exclude={"request_id"})
        with Session(self.engine) as session, session.begin():
            if request.mail_id:
                self._mail(session, owner, request.mail_id)
            todo_id, stamp = identifier("todo"), now()
            session.execute(
                insert(Todo)
                .values(
                    todo_id=todo_id,
                    user_id=owner.user_id,
                    account_id=owner.account_id,
                    request_id=request.request_id,
                    request_payload=payload,
                    mail_id=request.mail_id,
                    title=request.title,
                    due=request.due,
                    created_at=stamp,
                    updated_at=stamp,
                )
                .on_conflict_do_nothing(constraint="uq_f5_todo_request")
            )
            row = session.scalar(
                self._owned(Todo, owner).where(Todo.request_id == request.request_id)
            )
            if row.request_payload != payload:
                raise F5Error("request_id_reused")
            return TodoView.model_validate(row)

    def list_todos(self, owner, *, status=None, limit=20, cursor=None):
        with Session(self.engine) as session:
            query = self._owned(Todo, owner)
            if status:
                query = query.where(Todo.status == status)
            rows, next_cursor = self._page(session, query, Todo, "todo_id", limit, cursor)
            return TodoPage(
                items=[TodoView.model_validate(r) for r in rows], next_cursor=next_cursor
            )

    def update_todo(self, owner, todo_id, request):
        with Session(self.engine) as session, session.begin():
            row = session.scalar(
                self._owned(Todo, owner).where(Todo.todo_id == todo_id).with_for_update()
            )
            if row is None:
                raise F5Error("not_found", 404)
            if row.version != request.version:
                raise F5Error("stale_version")
            for key, value in request.model_dump(exclude_unset=True, exclude={"version"}).items():
                setattr(row, key, value)
            row.updated_at, row.version = now(), row.version + 1
            session.flush()
            return TodoView.model_validate(row)

    def events(self, owner, *, limit=100):
        if not 1 <= limit <= 100:
            raise F5Error("invalid_limit", 422)
        with Session(self.engine) as session:
            rows = session.execute(
                self._owned(Outbox, owner)
                .join(Suggestion, Outbox.suggestion_id == Suggestion.suggestion_id)
                .add_columns(Suggestion.mail_id, Suggestion.type)
                .where(Outbox.delivered_at.is_(None), Suggestion.status == "pending")
                .order_by(Outbox.created_at, Outbox.event_id)
                .limit(limit)
            )
            return EventPage(
                items=[
                    SuggestionEvent(
                        event_id=row.event_id,
                        suggestion_id=row.suggestion_id,
                        mail_id=mail_id,
                        type=kind,
                        created_at=row.created_at,
                    )
                    for row, mail_id, kind in rows
                ]
            )

    def ack_event(self, owner, event_id):
        with Session(self.engine) as session, session.begin():
            # 승인·무시와 잠금 순서를 맞춘다. 먼저 읽은 뒤 제안을 잠근다.
            query = self._owned(Outbox, owner).where(Outbox.event_id == event_id)
            event = session.scalar(query)
            if event is None:
                raise F5Error("not_found", 404)
            row = self._suggestion(session, owner, event.suggestion_id, lock=True)
            event = session.scalar(
                query.with_for_update().execution_options(populate_existing=True)
            )
            if row.status != "pending":
                return
            if event.delivered_at is None:
                event.delivered_at = now()
                row.notified_at = event.delivered_at
