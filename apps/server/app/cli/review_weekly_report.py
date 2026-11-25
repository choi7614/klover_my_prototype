"""가짜 메일 전용 F4 검토 서버. 계정·키·운영 DB·Gmail을 읽지 않는다."""

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine

from app.api.mail_read import MailAPIContext
from app.api.weekly_report import register_weekly_report_api
from app.connectors.fixture import load_fixture_mails
from app.db.repositories.report_mail import InMemoryReportMailRepository
from app.db.repositories.weekly_report import SQLWeeklyReportRepository, report_metadata
from app.main import create_app
from app.schemas.mail_api import LocalSession
from app.services.weekly_report import WeeklyReportService
from app.testing.weekly_report import FixtureReportProfile, FixtureWeeklyGenerator


class ReviewSession:
    def session(self):
        return LocalSession(
            user_id="demo-hong",
            account_id="f4-synthetic-account",
            email="hong@example.test",
            sync_started_at=datetime(2026, 9, 20, tzinfo=UTC),
        )


def main():
    parser = argparse.ArgumentParser(description="F4 가짜 메일·테스트 대역 검토 서버")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True, help="검토 전용 SQLite 파일")
    parser.add_argument("--token-file", type=Path, required=True, help="임시 검토 토큰 파일")
    parser.add_argument("--test-double", action="store_true", required=True)
    parser.add_argument("--port", type=int, default=8014)
    args = parser.parse_args()
    token = args.token_file.read_text().strip()
    if len(token) != 43:
        parser.error("검토 토큰 파일을 확인하세요")
    if args.database.exists():
        # 재조회 실험은 검토 파일 표식이 있는 DB만 재사용한다.
        try:
            with sqlite3.connect(
                f"{args.database.resolve().as_uri()}?mode=ro", uri=True
            ) as connection:
                marker = connection.execute("PRAGMA application_id").fetchone()[0]
            if marker != 0x46345250:
                parser.error("기존 DB를 검토 DB로 사용하지 않습니다")
        except sqlite3.DatabaseError:
            parser.error("기존 파일을 검토 DB로 사용하지 않습니다")
    else:
        args.database.touch(mode=0o600, exist_ok=False)
        with sqlite3.connect(args.database) as connection:
            connection.execute("PRAGMA application_id = 1177834064")
    engine = create_engine(f"sqlite:///{args.database.resolve()}", hide_parameters=True)
    report_metadata.create_all(engine)
    service = WeeklyReportService(
        mails=InMemoryReportMailRepository(load_fixture_mails(args.fixture)),
        profiles=FixtureReportProfile(),
        reports=SQLWeeklyReportRepository(engine),
        generator=FixtureWeeklyGenerator(),
        now=lambda: datetime(2026, 10, 12, 0, tzinfo=UTC),
    )
    application = create_app()
    application.state.mail_api = MailAPIContext(token, ReviewSession())
    register_weekly_report_api(application, service)
    uvicorn.run(application, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
