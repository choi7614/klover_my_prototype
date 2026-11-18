"""실제 로컬 API를 호출하되 메일·계정·인증 정보 대신 상태와 개수만 출력한다."""

import argparse
import json
import logging

import httpx

from app.mail_api_config import read_api_token
from app.schemas.mail_api import LocalSession, MailDetail, MailPage


def main():
    parser = argparse.ArgumentParser(description="로컬 메일 API 상태 확인")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("포트는 1~65535 숫자여야 합니다")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{args.port}",
            headers={"Authorization": "Bearer " + read_api_token()},
            trust_env=False,
            follow_redirects=False,
            timeout=10,
        ) as client:
            response = client.get("/auth/session")
            response.raise_for_status()
            LocalSession.model_validate(response.json())
            response = client.get("/mails", params={"limit": 20})
            response.raise_for_status()
            page = MailPage.model_validate(response.json())
            detail = "empty"
            if page.items:
                response = client.get("/mails/" + page.items[0].mail_id)
                response.raise_for_status()
                MailDetail.model_validate(response.json())
                detail = "ok"
    except Exception:
        raise SystemExit(
            "메일 API를 확인하지 못했습니다. 전용 서버 실행·포트·API 설정을 확인하세요."
        ) from None
    print(
        json.dumps(
            {
                "status": "ok",
                "session": "ok",
                "listed": len(page.items),
                "detail": detail,
                "has_next_page": page.next_cursor is not None,
            }
        )
    )


if __name__ == "__main__":
    main()
