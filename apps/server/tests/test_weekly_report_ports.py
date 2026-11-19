import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database
from test_weekly_report import ACTOR, FIXTURE, NOW, generate

from app.connectors.fixture import load_fixture_mails
from app.db.models import Mail, MailAccount, User
from app.db.repositories.report_mail import InMemoryReportMailRepository
from app.db.repositories.report_source import SQLReportMailRepository
from app.db.repositories.weekly_report import SQLWeeklyReportRepository, report_metadata
from app.schemas.report import ReportPeriod
from app.services.report import ReportInputNotReadyError, prepare_weekly_report_input
from app.services.report_ports import ReportAnalysis
from app.services.weekly_report import WeeklyReportService
from app.testing.weekly_report import FixtureReportProfile, FixtureWeeklyGenerator

PERIOD = ReportPeriod(start="2026-10-05", end="2026-10-09")


class Analyses:
    def __init__(self, rows):
        self.rows = rows
        self.seen = None

    async def read_for_report(self, **request):
        self.seen = request
        return self.rows


def read_source(repository):
    return asyncio.run(
        prepare_weekly_report_input(repository=repository, user_id="user-a", period=PERIOD)
    )


def seed(engine, status="done"):
    with Session(engine) as session, session.begin():
        for user in ("user-a", "user-b"):
            session.add(User(user_id=user))
        session.flush()
        for user in ("user-a", "user-b"):
            session.add(
                MailAccount(
                    account_id=user + "-account",
                    user_id=user,
                    source="fixture",
                    email=user + "@example.test",
                    sync_started_at=PERIOD.start_at,
                )
            )
        session.flush()
        for identifier, user, stamp, direction in (
            ("start", "user-a", datetime(2026, 10, 4, 15, tzinfo=UTC), "received"),
            ("end", "user-a", datetime(2026, 10, 9, 14, 59, 59, tzinfo=UTC), "sent"),
            ("before", "user-a", datetime(2026, 10, 4, 14, 59, 59, tzinfo=UTC), "received"),
            ("after", "user-a", datetime(2026, 10, 9, 15, tzinfo=UTC), "received"),
            ("foreign", "user-b", datetime(2026, 10, 7, tzinfo=UTC), "received"),
        ):
            session.add(
                Mail(
                    mail_id=identifier,
                    source_message_id=identifier,
                    user_id=user,
                    account_id=user + "-account",
                    direction=direction,
                    mailbox="sent" if direction == "sent" else "inbox",
                    thread_id="thread-a",
                    from_addr="synthetic@example.test",
                    to=[{"addr": "receiver@example.test"}],
                    subject="합성 테스트",
                    body_text="가짜 본문",
                    received_at=stamp,
                    analysis_status=status,
                )
            )


def test_real_database_source_uses_existing_owner_and_korean_date_contract(database):
    engine, _ = database
    seed(engine)
    analyses = Analyses(
        [
            ReportAnalysis(
                mail_id=identifier,
                user_id="user-a",
                analysis_status="done",
                category="work_request",
            )
            for identifier in ("start", "end")
        ]
    )
    result = read_source(SQLReportMailRepository(engine, analyses))
    assert result.groups[0].mail_ids == ("start", "end")
    assert result.scope.total == 2 and analyses.seen["mail_ids"] == ("start", "end")
    assert result.groups[0].mails[1].direction == "sent"


def test_database_done_flag_without_analysis_data_does_not_fabricate_results(database):
    engine, _ = database
    seed(engine)
    with pytest.raises(ReportInputNotReadyError) as error:
        read_source(SQLReportMailRepository(engine))
    assert error.value.mail_ids == ("start", "end")


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_database_pending_or_failed_cannot_be_overridden_by_stale_analysis(database, status):
    engine, _ = database
    seed(engine, status)
    analyses = Analyses(
        [
            ReportAnalysis(
                mail_id=identifier,
                user_id="user-a",
                analysis_status="done",
                category="work_request",
            )
            for identifier in ("start", "end")
        ]
    )
    with pytest.raises(ReportInputNotReadyError):
        read_source(SQLReportMailRepository(engine, analyses))


@pytest.mark.parametrize("invalid", ["foreign_owner", "unknown_id", "duplicate_id"])
def test_analysis_port_rejects_owner_unknown_and_duplicate_results(database, invalid):
    engine, _ = database
    seed(engine)
    values = dict(
        mail_id="start", user_id="user-a", analysis_status="done", category="work_request"
    )
    if invalid == "foreign_owner":
        values["user_id"] = "user-b"
    if invalid == "unknown_id":
        values["mail_id"] = "missing"
    rows = [ReportAnalysis(**values)] * (2 if invalid == "duplicate_id" else 1)
    with pytest.raises(ValueError, match="분석 포트"):
        read_source(SQLReportMailRepository(engine, Analyses(rows)))


def test_postgresql_report_payload_round_trip_and_owner_filter(database):
    engine, _ = database
    report_metadata.create_all(engine)  # 이 테스트만의 임시 스키마. 운영 등록이 아니다.
    service = WeeklyReportService(
        mails=InMemoryReportMailRepository(load_fixture_mails(FIXTURE)),
        profiles=FixtureReportProfile(),
        reports=SQLWeeklyReportRepository(engine),
        generator=FixtureWeeklyGenerator(),
        now=lambda: NOW,
    )
    document = generate(service)
    engine.dispose()
    assert asyncio.run(service.get(ACTOR, document.report_id)) == document
    assert (
        asyncio.run(service.reports.get(user_id="different", report_id=document.report_id)) is None
    )
