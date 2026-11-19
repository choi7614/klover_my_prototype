"""메일 내용·주소·토큰을 출력하지 않는 로컬 동기화·조회 명령."""

import argparse
import json
import logging

from sqlalchemy.exc import SQLAlchemyError

from app.connectors.gmail_mail import GmailMailClient
from app.db.config import database_engine
from app.db.repositories.gmail_sync import GmailSyncRepository
from app.google_config import GoogleConnectionError, load_settings
from app.services.gmail_sync import synchronize


def main():
    parser = argparse.ArgumentParser(description="연결한 테스트 Gmail의 새 받은 메일 저장·조회")
    parser.add_argument("action", choices=["sync", "list"])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    engine = None
    try:
        settings = load_settings()
        engine = database_engine()
        repository = GmailSyncRepository(engine, settings)
        if args.action == "sync":
            with GmailMailClient(settings) as client:
                result = {"status": "ok", **synchronize(repository, client)}
        else:
            rows = repository.list_received(args.limit)
            result = {"status": "ok", "count": len(rows), "mails": rows}
    except KeyboardInterrupt:
        raise SystemExit("수신 작업을 중단했습니다. 기존 데이터는 보존됩니다.") from None
    except GoogleConnectionError as error:
        # 이 타입은 커넥터·저장소가 만든 고정 안내이며 외부 응답을 포함하지 않는다.
        raise SystemExit(str(error)) from None
    except SQLAlchemyError:
        raise SystemExit(
            "DB를 확인하지 못했습니다. Docker 실행·DB 설정·마이그레이션을 확인하세요."
        ) from None
    except Exception:
        raise SystemExit(
            "작업을 완료하지 못했습니다. DB·설정·Google 연결 권한과 네트워크를 확인하세요. "
            "권한이 만료됐다면 기존 키를 보존하고 Google에 다시 연결하세요."
        ) from None
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
