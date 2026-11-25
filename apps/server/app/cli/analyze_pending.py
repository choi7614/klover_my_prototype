"""본문·키·메일 ID를 출력하지 않는 F1 전용 명시적 실행 명령."""

import argparse
import asyncio
import json

from sqlalchemy.exc import SQLAlchemyError

from app.ai.interfaces import ProvidersNotConfigured
from app.ai.runtime import is_external, load_providers
from app.db.config import DatabaseConfigurationError, database_engine
from app.db.repositories.mail_analysis import AnalysisRepository
from app.pipeline.pending_analysis import process_pending


class ExternalTransferBlocked(Exception):
    pass


def main(argv=None):
    parser = argparse.ArgumentParser(description="F1 저장 준비 확인 또는 pending 분석 명시 실행")
    parser.add_argument("action", choices=["check", "run"])
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--limit", type=int, choices=range(1, 101), default=20, metavar="1~100")
    parser.add_argument("--mail-id")
    parser.add_argument("--reanalyze", action="store_true")
    parser.add_argument(
        "--allow-gmail-content",
        action="store_true",
        help="별도 승인된 Gmail 본문 분석에서만 명시. 기본은 fixture만 처리",
    )
    args = parser.parse_args(argv)
    if args.reanalyze and not args.mail_id:
        parser.error("--reanalyze에는 --mail-id가 필요합니다")
    engine = None
    try:
        # 제공자가 없을 때 DB 연결·메일 로드·상태 변경도 하지 않는다.
        providers = load_providers() if args.action == "run" else None
        if providers is not None and args.allow_gmail_content and is_external(providers[0]):
            # 보안 확인 전까지 실제 Gmail 본문을 외부 AI(Claude)로 보내지 않는다(open-questions 14).
            raise ExternalTransferBlocked
        engine = database_engine()
        repository = AnalysisRepository(engine, user_id=args.user_id, account_id=args.account_id)
        ready = repository.readiness(allow_gmail=args.allow_gmail_content)
        if args.action == "check":
            output = {"status": "checked", **ready, "providers_ready": False}
        elif not ready["storage_ready"]:
            output = {"status": "storage_not_integrated"}
        else:
            batch = asyncio.run(
                process_pending(
                    repository,
                    *providers,
                    limit=args.limit,
                    allow_gmail=args.allow_gmail_content,
                    mail_id=args.mail_id,
                    reanalyze=args.reanalyze,
                )
            )
            output = {"status": "completed", "done": batch.done, "failed": batch.failed}
            if any(item.failure_code == "provider_error" for item in batch.outcomes):
                output["hint"] = (
                    "AI 호출 실패: python -m app.cli.check_ai --ping 으로 원인을 확인하세요"
                )
    except ExternalTransferBlocked:
        output = {
            "status": "external_transfer_blocked",
            "done": 0,
            "failed": 0,
            "reason": (
                "Claude(외부 AI)로는 실제 Gmail 본문을 분석하지 않습니다. 로컬 Ollama를 쓰세요"
            ),
        }
    except ProvidersNotConfigured as error:
        # 설정 안내 문구는 고정 문장이며 키·주소 값을 담지 않는다.
        output = {"status": "not_configured", "done": 0, "failed": 0, "reason": str(error)}
    except (SQLAlchemyError, DatabaseConfigurationError):
        output = {"status": "storage_unavailable"}
    except KeyboardInterrupt:
        output = {"status": "interrupted"}
    except Exception:
        output = {"status": "analysis_unavailable"}
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(output, ensure_ascii=False))
    ready = output["status"] == "checked" and output["storage_ready"]
    completed = output["status"] == "completed" and not output.get("failed")
    return 0 if ready or completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
