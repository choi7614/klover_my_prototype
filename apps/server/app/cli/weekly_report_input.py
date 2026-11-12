import argparse
import asyncio
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.connectors.fixture import load_fixture_mails
from app.db.repositories.report_mail import InMemoryReportMailRepository
from app.schemas.report import ReportPeriod
from app.services.report import prepare_weekly_report_input


def main() -> None:
    parser = argparse.ArgumentParser(description="가짜 메일로 F4 보고 입력을 준비합니다")
    parser.add_argument("--fixture", required=True, type=Path, help="가짜 메일 JSON 파일")
    parser.add_argument("--user-id", required=True, help="fixture에서 조회할 사용자 ID")
    parser.add_argument("--start", required=True, type=date.fromisoformat, help="시작일 YYYY-MM-DD")
    parser.add_argument("--end", required=True, type=date.fromisoformat, help="종료일 YYYY-MM-DD")
    args = parser.parse_args()

    try:
        period = ReportPeriod(start=args.start, end=args.end)
        repository = InMemoryReportMailRepository(load_fixture_mails(args.fixture))
        result = asyncio.run(
            prepare_weekly_report_input(repository=repository, user_id=args.user_id, period=period)
        )
    except ValidationError:
        parser.error("날짜 또는 가짜 메일 파일 형식을 확인하세요")
    except OSError:
        parser.error("가짜 메일 파일을 읽을 수 없습니다")
    except ValueError as error:
        parser.error(str(error))

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
