"""F1이 저장한 분석 결과로 F5 제안을 수동으로 만드는 명령. 본문·근거·키를 출력하지 않는다.

    uv run python -m app.cli.f5_scan --user-id U --account-id A --mail-id M

제안을 '저장'만 한다. 캘린더 등록·할 일 추가·회신은 사용자가 앱에서 승인해야 실행된다.
"""

import argparse
import asyncio
import json
from collections import Counter

from sqlalchemy.exc import SQLAlchemyError

from app.ai.interfaces import ProvidersNotConfigured
from app.ai.runtime import load_generation
from app.db.config import DatabaseConfigurationError, database_engine
from app.db.repositories.f5 import F5Repository
from app.pipeline.scan_analysis import ScanFailed
from app.schemas.f5 import Principal
from app.services.f5 import F5Service
from app.services.f5_errors import F5Error

HINTS = {
    "provider_error": "AI 호출 실패: python -m app.cli.check_ai --ping 으로 원인을 확인하세요",
    "timeout": "AI 응답이 시간 안에 오지 않았습니다. 로컬 모델이면 잠시 뒤 다시 실행하세요",
    "invalid_response": (
        "AI가 두 번 모두 형식을 지키지 않았습니다. 다른 모델로 바꾸거나 다시 실행하세요"
    ),
    "external_transfer_blocked": (
        "실제 Gmail 본문은 --allow-gmail-content와 로컬 Ollama에서만 스캔합니다"
    ),
    "analysis_mismatch": "분석 뒤 본문이 바뀌었습니다. F1 재분석 후 다시 실행하세요",
}


def main(argv=None):
    parser = argparse.ArgumentParser(description="F1 분석 결과로 F5 제안 만들기(저장만, 실행 없음)")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--mail-id", required=True)
    parser.add_argument(
        "--allow-gmail-content",
        action="store_true",
        help="별도 승인된 Gmail 본문에서만 명시. 기본은 fixture 메일만 처리",
    )
    args = parser.parse_args(argv)
    engine = None
    try:
        owner = Principal(user_id=args.user_id, account_id=args.account_id)
        generator = load_generation()
        engine = database_engine()
        repository = F5Repository(engine)
        analysis = repository.stored_analysis(owner, args.mail_id)
        if analysis is None:
            output = {"status": "analysis_not_found"}
        else:
            outcome = asyncio.run(
                F5Service(repository).scan_from_analysis(
                    owner,
                    args.mail_id,
                    analysis,
                    generator,
                    allow_gmail=args.allow_gmail_content,
                )
            )
            output = {
                "status": outcome.status,
                "created": len(outcome.result.created_ids),
                "total": len(outcome.result.items),
                "skipped": dict(Counter(item.reason for item in outcome.skipped)),
                "attempts": outcome.attempts,
            }
    except ScanFailed as error:
        output = {"status": "failed", "failure_code": error.code}
        if error.code in HINTS:
            output["hint"] = HINTS[error.code]
    except ProvidersNotConfigured as error:
        output = {"status": "not_configured", "reason": str(error)}
    except F5Error as error:
        output = {"status": "failed", "failure_code": error.code}
    except ValueError:
        output = {"status": "invalid_arguments"}
    except (SQLAlchemyError, DatabaseConfigurationError):
        output = {"status": "storage_unavailable"}
    except KeyboardInterrupt:
        output = {"status": "interrupted"}
    except Exception:
        output = {"status": "scan_unavailable"}
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(output, ensure_ascii=False))
    return 0 if output["status"] in {"created", "unchanged", "nothing_to_suggest"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
