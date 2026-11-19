"""F4 전용 저장소. 공통 Base·기존 마이그레이션과 자동 등록하지 않는다."""

from typing import Protocol

from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.schemas.weekly_report import StoredWeeklyReport

report_metadata = MetaData()
weekly_reports = Table(
    "weekly_reports",
    report_metadata,
    Column("report_id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("selection_key", Text, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("payload", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    UniqueConstraint("user_id", "selection_key", name="uq_weekly_report_owner_selection"),
)


class ReportConflictError(ValueError):
    pass


class WeeklyReportRepository(Protocol):
    async def get(self, *, user_id: str, report_id: str) -> StoredWeeklyReport | None: ...

    async def find(self, *, user_id: str, selection_key: str) -> StoredWeeklyReport | None: ...

    async def create(self, report: StoredWeeklyReport) -> None: ...

    async def replace(self, report: StoredWeeklyReport, *, expected_revision: int) -> None: ...


class SQLWeeklyReportRepository:
    def __init__(self, engine):
        self.engine = engine

    def _read(self, user_id, condition):
        with self.engine.connect() as connection:
            payload = connection.scalar(
                select(weekly_reports.c.payload).where(
                    weekly_reports.c.user_id == user_id, condition
                )
            )
        return StoredWeeklyReport.model_validate(payload) if payload is not None else None

    async def get(self, *, user_id, report_id):
        return await run_in_threadpool(self._read, user_id, weekly_reports.c.report_id == report_id)

    async def find(self, *, user_id, selection_key):
        return await run_in_threadpool(
            self._read, user_id, weekly_reports.c.selection_key == selection_key
        )

    def _write(self, report, expected_revision):
        values = dict(
            report_id=report.document.report_id,
            user_id=report.user_id,
            selection_key=report.selection_key,
            revision=report.document.revision,
            payload=report.model_dump(mode="json", round_trip=True),
        )
        try:
            with self.engine.begin() as connection:
                if expected_revision is None:
                    connection.execute(insert(weekly_reports).values(**values))
                else:
                    result = connection.execute(
                        update(weekly_reports)
                        .where(
                            weekly_reports.c.report_id == report.document.report_id,
                            weekly_reports.c.user_id == report.user_id,
                            weekly_reports.c.revision == expected_revision,
                        )
                        .values(**values)
                    )
                    if result.rowcount != 1:
                        raise ReportConflictError("저장본이 변경되었습니다. 다시 확인해 주세요")
        except IntegrityError:
            raise ReportConflictError("같은 선택의 보고서가 이미 저장되었습니다") from None

    async def create(self, report):
        await run_in_threadpool(self._write, report, None)

    async def replace(self, report, *, expected_revision):
        await run_in_threadpool(self._write, report, expected_revision)
