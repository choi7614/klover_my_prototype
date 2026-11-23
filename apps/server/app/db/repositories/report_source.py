"""기존 DB 기본 메일과 F1 분석 읽기 포트를 합친다. Gmail·토큰은 읽지 않는다."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db.models import Mail, MailAccount
from app.schemas.report import ReportMail
from app.services.report_ports import ReportAnalysisPort


class SQLReportMailRepository:
    def __init__(self, engine, analyses: ReportAnalysisPort | None = None):
        self.engine, self.analyses = engine, analyses

    def _read(self, user_id, start_at, end_before):
        with Session(self.engine) as session:
            rows = session.scalars(
                select(Mail)
                .join(
                    MailAccount,
                    (Mail.account_id == MailAccount.account_id)
                    & (Mail.user_id == MailAccount.user_id),
                )
                .where(
                    Mail.user_id == user_id,
                    Mail.direction.in_(("received", "sent")),
                    Mail.received_at >= start_at,
                    Mail.received_at < end_before,
                    (Mail.received_at >= MailAccount.sync_started_at)
                    | Mail.history_imported.is_(True),
                )
                .order_by(Mail.received_at, Mail.mail_id)
            ).all()
            return [
                dict(
                    mail_id=row.mail_id,
                    user_id=row.user_id,
                    thread_id=row.thread_id,
                    direction=row.direction,
                    received_at=row.received_at,
                    from_addr=row.from_addr,
                    from_name=row.from_name,
                    to=row.to,
                    subject=row.subject,
                    body_text=row.body_text,
                    analysis_status=row.analysis_status,
                )
                for row in rows
            ]

    async def list_received_and_sent(self, *, user_id, start_at, end_before):
        rows = await run_in_threadpool(self._read, user_id, start_at, end_before)
        identifiers = tuple(row["mail_id"] for row in rows)
        analyses = (
            await self.analyses.read_for_report(user_id=user_id, mail_ids=identifiers)
            if self.analyses is not None and identifiers
            else ()
        )
        by_id = {}
        for analysis in analyses:
            if (
                analysis.user_id != user_id
                or analysis.mail_id not in identifiers
                or analysis.mail_id in by_id
            ):
                raise ValueError("분석 포트가 사용자·메일 조회 계약을 위반했습니다")
            by_id[analysis.mail_id] = analysis
        result = []
        for row in rows:
            analysis = by_id.get(row["mail_id"])
            if analysis is not None:
                stored_status = row["analysis_status"]
                row.update(analysis.model_dump(exclude={"mail_id", "user_id"}))
                if stored_status != "done":
                    row["analysis_status"] = stored_status
            result.append(ReportMail.model_validate(row))
        return tuple(result)
