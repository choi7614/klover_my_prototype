"""가져오기 전용 작업·메일 저장. 일반 수신 커서와 시작 시점은 변경하지 않는다."""

from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import HistoryImportJob, Mail, MailAccount
from app.db.repositories.mail import MailRepository


class HistoryRepository:
    def __init__(self, engine, owner):
        self.engine, self.owner = engine, owner

    def _jobs(self):
        return select(HistoryImportJob).where(
            HistoryImportJob.user_id == self.owner.user_id,
            HistoryImportJob.account_id == self.owner.account_id,
        )

    @contextmanager
    def locked(self, job_id=None):
        with Session(self.engine) as session, session.begin():
            # 단기간 계정 행 잠금으로 중복 작업 시작만 직렬화. 네트워크 대기는 잠금 밖이다.
            session.scalar(
                select(MailAccount)
                .where(
                    MailAccount.account_id == self.owner.account_id,
                    MailAccount.user_id == self.owner.user_id,
                )
                .with_for_update()
            )
            rows = list(session.scalars(self._jobs().with_for_update()))
            row = next((x for x in rows if x.job_id == job_id), None)
            yield session, rows, row

    def list(self):
        with Session(self.engine) as session:
            rows = session.scalars(self._jobs())
            return sorted(
                [dict(x.payload) for x in rows], key=lambda x: x["created_at"], reverse=True
            )[:20]

    def get(self, job_id):
        with Session(self.engine) as session:
            row = session.scalar(self._jobs().where(HistoryImportJob.job_id == job_id))
            return dict(row.payload) if row else None

    def create(self, start, end):
        with self.locked() as (session, rows, _):
            if any(x.payload["status"] == "running" for x in rows):
                raise ValueError("busy")
            data = dict(
                job_id=uuid4().hex,
                start=start.isoformat(),
                end=end.isoformat(),
                status="paused",
                saved=0,
                skipped=0,
                processed=0,
                page_token=None,
                page_done=[],
                pages=0,
                error=None,
                created_at=datetime.now(UTC).isoformat(),
            )
            session.add(
                HistoryImportJob(
                    job_id=data["job_id"],
                    user_id=self.owner.user_id,
                    account_id=self.owner.account_id,
                    payload=data,
                )
            )
            return data

    def transition(self, job_id, action):
        with self.locked(job_id) as (_, rows, row):
            if row is None:
                return None
            data = dict(row.payload)
            if action == "resume":
                if data["status"] not in {"paused", "failed"} or any(
                    x.payload["status"] == "running" for x in rows
                ):
                    raise ValueError("busy")
                if data["processed"] >= 10000 or data["pages"] >= 1000:
                    raise ValueError("limit")
                if data.get("error") == "page_expired":
                    data.update(page_token=None, page_done=[])
                data.update(status="running", error=None, run_id=uuid4().hex)
            elif data["status"] == "running":
                data["status"] = "paused"
            row.payload = data
            return data

    def checkpoint(
        self,
        job_id,
        *,
        source_id=None,
        message=None,
        page_token=None,
        page_end=False,
        failure=None,
        expected_run_id=None,
    ):
        with self.locked(job_id) as (session, _, row):
            if (
                row is None
                or row.payload["status"] != "running"
                or (expected_run_id is not None and row.payload.get("run_id") != expected_run_id)
            ):
                return False
            data = dict(row.payload)
            if failure:
                data.update(status="failed", error=failure)
            elif page_end:
                data.update(page_token=page_token, page_done=[], pages=data["pages"] + 1)
                if not page_token:
                    data["status"] = "completed"
            elif source_id not in data["page_done"]:
                existing = session.scalar(
                    select(Mail.mail_id).where(
                        Mail.user_id == self.owner.user_id,
                        Mail.account_id == self.owner.account_id,
                        Mail.source_message_id == source_id,
                    )
                )
                if message is not None and existing is None:
                    MailRepository(session).store_received(
                        user_id=self.owner.user_id,
                        account_id=self.owner.account_id,
                        mail_id=uuid4().hex,
                        source_message_id=message.source_id,
                        received_at=message.received_at,
                        from_addr=message.from_addr,
                        from_name=message.from_name,
                        to=message.to,
                        cc=message.cc,
                        subject=message.subject,
                        body_text=message.body_text,
                        thread_id=message.thread_id,
                        is_read=message.is_read,
                        history_imported=True,
                    )
                    data["saved"] += 1
                else:
                    data["skipped"] += 1
                data["processed"] += 1
                data["page_done"] = [*data["page_done"], source_id]
            row.payload = data
            return True

    def recover(self):
        with self.locked() as (_, rows, _row):
            for row in rows:
                if row.payload["status"] == "running":
                    row.payload = {**row.payload, "status": "paused", "error": "server_restarted"}
