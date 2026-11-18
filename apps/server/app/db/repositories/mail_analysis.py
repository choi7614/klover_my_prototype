"""F1 전용 저장 경계. 스키마 설치는 하지 않으며 각 메일을 원자적으로 처리한다."""

import json
from contextlib import contextmanager
from datetime import datetime
from typing import get_args
from uuid import uuid4

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.ai.interfaces import ProviderIdentity, ProvidersNotConfigured
from app.db.models import Mail, MailAccount
from app.pipeline.embed import body_chunks, validate_vectors
from app.schemas.mail_analysis import AnalysisMail, AnalysisResult, CategoryExample
from app.schemas.report import MailCategory, ReportMail


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


class AnalysisRepository:
    def __init__(
        self, engine: Engine, *, user_id: str, account_id: str, allow_test_providers: bool = False
    ):
        if not user_id or not account_id:
            raise ValueError("사용자·계정을 명시해야 합니다")
        self.engine = engine
        self.user_id = user_id
        self.account_id = account_id
        self.allow_test_providers = allow_test_providers
        if allow_test_providers:
            with engine.connect() as connection:
                database, schema = connection.execute(
                    text("SELECT current_database(), current_schema()")
                ).one()
                if not database.endswith("_test") or not schema.startswith("f1_test_"):
                    raise ValueError("테스트 제공자는 분리된 F1 테스트 DB·스키마에서만 허용됩니다")

    def _query(self):
        return (
            select(Mail, MailAccount.source)
            .join(
                MailAccount,
                (MailAccount.account_id == Mail.account_id) & (MailAccount.user_id == Mail.user_id),
            )
            .where(
                Mail.user_id == self.user_id,
                Mail.account_id == self.account_id,
                Mail.received_at >= MailAccount.sync_started_at,
            )
        )

    def readiness(self, *, allow_gmail: bool = False) -> dict:
        with self.engine.connect() as connection:
            tables = connection.execute(
                text(
                    "SELECT to_regclass('f1_mail_analysis'), to_regclass('f1_mail_chunks'), "
                    "to_regclass('f1_category_feedback')"
                )
            ).one()
            if not all(tables):
                return {"storage_ready": False, "pending": None}
            pending = connection.scalar(
                text("""
                    SELECT count(*) FROM mails m JOIN mail_accounts a
                      ON a.account_id=m.account_id AND a.user_id=m.user_id
                    WHERE m.user_id=:user_id AND m.account_id=:account_id
                      AND m.direction='received' AND m.analysis_status='pending'
                      AND m.mailbox IN ('inbox','archive')
                      AND m.received_at >= a.sync_started_at
                      AND (:allow_gmail OR a.source='fixture')
                """),
                {
                    "user_id": self.user_id,
                    "account_id": self.account_id,
                    "allow_gmail": allow_gmail,
                },
            )
            return {"storage_ready": True, "pending": pending}

    @contextmanager
    def claim(self, *, allow_gmail=False, mail_id=None, reanalyze=False):
        if reanalyze and mail_id is None:
            raise ValueError("재분석할 메일 ID를 명시해야 합니다")
        with Session(self.engine) as session, session.begin():
            query = self._query().where(
                Mail.direction == "received", Mail.mailbox.in_(["inbox", "archive"])
            )
            if not allow_gmail:
                query = query.where(MailAccount.source == "fixture")
            if not reanalyze:
                query = query.where(Mail.analysis_status == "pending")
            if mail_id is not None:
                query = query.where(Mail.mail_id == mail_id)
            row = session.execute(
                query.order_by(Mail.received_at, Mail.mail_id)
                .limit(1)
                .with_for_update(skip_locked=True, of=Mail)
            ).first()
            yield AnalysisTransaction(self, session, *row) if row else None

    def set_category(self, mail_id: str, category: MailCategory) -> bool:
        if category not in get_args(MailCategory):
            raise ValueError("지원하지 않는 분류입니다")
        with Session(self.engine) as session, session.begin():
            row = session.execute(
                self._query().where(Mail.mail_id == mail_id).with_for_update(of=Mail)
            ).first()
            if row is None:
                return False
            mail, _ = row
            params = {
                "mail_id": mail_id,
                "user_id": self.user_id,
                "account_id": self.account_id,
                "category": category,
            }
            existing = session.scalar(
                text("""
                    SELECT user_label FROM f1_mail_analysis
                    WHERE mail_id=:mail_id AND user_id=:user_id AND account_id=:account_id
                """),
                params,
            )
            if existing == category:
                return True
            session.execute(
                text("""
                INSERT INTO f1_mail_analysis (mail_id,user_id,account_id,user_label)
                VALUES (:mail_id,:user_id,:account_id,:category)
                ON CONFLICT (mail_id) DO UPDATE SET user_label=excluded.user_label,updated_at=now()
            """),
                params,
            )
            session.execute(
                text("""
                INSERT INTO f1_category_feedback
                  (mail_id,user_id,account_id,from_addr,subject,user_label)
                VALUES (:mail_id,:user_id,:account_id,:from_addr,:subject,:category)
            """),
                {**params, "from_addr": mail.from_addr, "subject": mail.subject},
            )
            session.execute(
                text("""
                UPDATE f1_mail_chunks SET category=:category
                WHERE mail_id=:mail_id AND user_id=:user_id AND account_id=:account_id
            """),
                params,
            )
        return True


class AnalysisTransaction:
    def __init__(self, repository, session, row, source):
        self.repository = repository
        self.session = session
        self.row = row
        self.mail = AnalysisMail(
            **{key: getattr(row, key) for key in AnalysisMail.model_fields if key != "source"},
            source=source,
        )

    def examples(self) -> tuple[CategoryExample, ...]:
        rows = self.session.execute(
            text("""
            SELECT subject,user_label FROM (
                SELECT DISTINCT ON (mail_id) mail_id,subject,user_label,feedback_id
                FROM f1_category_feedback
                WHERE user_id=:user_id AND account_id=:account_id AND from_addr=:from_addr
                ORDER BY mail_id,feedback_id DESC
            ) latest
            ORDER BY feedback_id DESC LIMIT 5
        """),
            {
                "user_id": self.mail.user_id,
                "account_id": self.mail.account_id,
                "from_addr": self.mail.from_addr,
            },
        )
        return tuple(CategoryExample(subject=row.subject, category=row.user_label) for row in rows)

    def _write_metadata(self, values):
        params = {
            "mail_id": self.mail.mail_id,
            "user_id": self.mail.user_id,
            "account_id": self.mail.account_id,
            **values,
        }
        self.session.execute(
            text("""
            INSERT INTO f1_mail_analysis
              (mail_id,user_id,account_id,category,summary,action_items,needs_reply,priority,
               priority_reason,entities,events,evidence_spans,failure_code,attempts,
               llm_provider,llm_model,llm_mode,embedding_provider,embedding_model,
               embedding_mode,embedding_dimensions)
            VALUES (:mail_id,:user_id,:account_id,:category,:summary,CAST(:action_items AS jsonb),
              :needs_reply,:priority,:priority_reason,CAST(:entities AS jsonb),
              CAST(:events AS jsonb),CAST(:evidence_spans AS jsonb),:failure_code,:attempts,
              :llm_provider,:llm_model,:llm_mode,:embedding_provider,:embedding_model,
              :embedding_mode,:embedding_dimensions)
            ON CONFLICT (mail_id) DO UPDATE SET
              category=excluded.category,summary=excluded.summary,action_items=excluded.action_items,
              needs_reply=excluded.needs_reply,priority=excluded.priority,
              priority_reason=excluded.priority_reason,entities=excluded.entities,
              events=excluded.events,evidence_spans=excluded.evidence_spans,
              failure_code=excluded.failure_code,attempts=excluded.attempts,
              llm_provider=excluded.llm_provider,llm_model=excluded.llm_model,llm_mode=excluded.llm_mode,
              embedding_provider=excluded.embedding_provider,embedding_model=excluded.embedding_model,
              embedding_mode=excluded.embedding_mode,embedding_dimensions=excluded.embedding_dimensions,
              updated_at=now()
        """),
            params,
        )

    def _clear_chunks(self):
        self.session.execute(
            text("""
            DELETE FROM f1_mail_chunks
            WHERE mail_id=:mail_id AND user_id=:user_id AND account_id=:account_id
        """),
            self.mail.model_dump(include={"mail_id", "user_id", "account_id"}),
        )

    def save_success(self, result, chunks, *, llm, embedding, dimensions, attempts):
        result = AnalysisResult.model_validate(result)
        result.check_source(self.mail)
        for identity in (llm, embedding):
            ProviderIdentity.model_validate(identity)
            if identity.mode == "test" and not self.repository.allow_test_providers:
                raise ProvidersNotConfigured("테스트 제공자의 운영 저장을 허용하지 않습니다")
        expected = [
            *(
                ("body", seq, content)
                for seq, content in enumerate(body_chunks(self.mail.body_text))
            ),
            ("summary", 0, result.summary),
        ]
        if [(chunk.kind, chunk.seq, chunk.text) for chunk in chunks] != expected:
            raise ValueError("청크가 본문·요약과 맞지 않습니다")
        validate_vectors(
            [chunk.vector for chunk in chunks], count=len(expected), dimensions=dimensions
        )
        values = result.model_dump(mode="json", exclude={"mail_id"})
        for key in ("action_items", "entities", "events", "evidence_spans"):
            values[key] = _json(values[key])
        values.update(
            failure_code=None,
            attempts=attempts,
            llm_provider=llm.provider,
            llm_model=llm.model,
            llm_mode=llm.mode,
            embedding_provider=embedding.provider,
            embedding_model=embedding.model,
            embedding_mode=embedding.mode,
            embedding_dimensions=dimensions,
        )
        self._write_metadata(values)
        category = self.session.scalar(
            text("""
            SELECT coalesce(user_label,category) FROM f1_mail_analysis WHERE mail_id=:mail_id
              AND user_id=:user_id AND account_id=:account_id
        """),
            self.mail.model_dump(include={"mail_id", "user_id", "account_id"}),
        )
        self._clear_chunks()
        for chunk in chunks:
            self.session.execute(
                text("""
                INSERT INTO f1_mail_chunks
                  (chunk_id,mail_id,user_id,account_id,kind,seq,text,embedding,
                   embedding_dimensions,embedding_provider,embedding_model,embedding_mode,
                   received_at,category)
                VALUES (:chunk_id,:mail_id,:user_id,:account_id,:kind,:seq,:text,
                  CAST(:embedding AS vector),:dimensions,:provider,:model,:mode,
                  :received_at,:category)
            """),
                {
                    "chunk_id": uuid4().hex,
                    "mail_id": self.mail.mail_id,
                    "user_id": self.mail.user_id,
                    "account_id": self.mail.account_id,
                    "kind": chunk.kind,
                    "seq": chunk.seq,
                    "text": chunk.text,
                    "embedding": _json(chunk.vector),
                    "dimensions": dimensions,
                    "provider": embedding.provider,
                    "model": embedding.model,
                    "mode": embedding.mode,
                    "received_at": self.mail.received_at,
                    "category": category,
                },
            )
        self.row.analysis_status = "done"

    def save_failure(self, code: str, attempts: int):
        if code not in {"invalid_response", "provider_error", "embedding_error", "input_too_large"}:
            raise ValueError("지원하지 않는 실패 코드입니다")
        self._write_metadata(
            {
                "category": None,
                "summary": None,
                "action_items": "[]",
                "needs_reply": None,
                "priority": None,
                "priority_reason": None,
                "entities": '{"projects":[],"orgs":[],"people":[]}',
                "events": "[]",
                "evidence_spans": "[]",
                "failure_code": code,
                "attempts": attempts,
                "llm_provider": None,
                "llm_model": None,
                "llm_mode": None,
                "embedding_provider": None,
                "embedding_model": None,
                "embedding_mode": None,
                "embedding_dimensions": None,
            }
        )
        self._clear_chunks()
        self.row.analysis_status = "failed"


class F1ReportMailRepository:
    """기존 ReportMailRepository의 읽기 계약. HTTP API에는 등록하지 않는다."""

    def __init__(self, repository: AnalysisRepository):
        self.repository = repository

    async def list_received_and_sent(
        self, *, user_id: str, start_at: datetime, end_before: datetime
    ) -> tuple[ReportMail, ...]:
        if any(
            value.tzinfo is None or value.utcoffset() is None for value in (start_at, end_before)
        ):
            raise ValueError("시각에는 시간대가 필요합니다")
        if end_before <= start_at:
            raise ValueError("기간 경계가 올바르지 않습니다")
        if user_id != self.repository.user_id:
            return ()
        with self.repository.engine.connect() as connection:
            rows = connection.execute(
                text("""
                SELECT m.*,a.category,a.user_label,a.summary,a.entities,a.llm_mode,a.embedding_mode
                FROM mails m JOIN mail_accounts account
                  ON account.account_id=m.account_id AND account.user_id=m.user_id
                LEFT JOIN f1_mail_analysis a ON a.mail_id=m.mail_id
                  AND a.user_id=m.user_id AND a.account_id=m.account_id
                WHERE m.user_id=:user_id AND m.account_id=:account_id
                  AND m.direction IN ('received','sent')
                  AND m.received_at>=:start_at AND m.received_at<:end_before
                  AND m.received_at>=account.sync_started_at
                ORDER BY m.received_at,m.mail_id
            """),
                {
                    "user_id": user_id,
                    "account_id": self.repository.account_id,
                    "start_at": start_at,
                    "end_before": end_before,
                },
            ).mappings()
            result = []
            for row in rows:
                values = {key: row[key] for key in ReportMail.model_fields if key in row}
                values["entities"] = values.get("entities") or {}
                if (row["llm_mode"] == "test" or row["embedding_mode"] == "test") and not (
                    self.repository.allow_test_providers
                ):
                    values.update(
                        analysis_status="pending", category=None, summary=None, entities={}
                    )
                result.append(ReportMail.model_validate(values))
            return tuple(result)
