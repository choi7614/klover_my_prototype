"""Electron 자동 검사 전용: 실제 FastAPI 읽기 라우터 + 합성 저장소. DB·Google 접근 없음."""

import argparse
from pathlib import Path

import uvicorn

from app.api.mail_read import MailAPIContext
from app.main import create_app

SESSION = {
    "user_id": "test-user",
    "account_id": "test-account",
    "email": "demo@example.invalid",
    "sync_started_at": "2026-11-19T00:00:00+09:00",
}


def mail(number):
    return {
        "mail_id": f"mail-{number}",
        "subject": f"합성 메일 {number}",
        "from_addr": "sender@example.invalid",
        "from_name": "검사용 발신자",
        "preview": "합성 미리보기",
        "received_at": "2026-11-19T01:00:00+09:00",
        "is_read": False,
        "analysis_status": "pending",
    }


class SyntheticRepository:
    def __init__(self):
        self.first_page_reads = 0

    def session(self):
        return SESSION

    def list(self, *, limit, cursor):
        assert limit == 20
        if cursor:
            assert cursor == "next-page"
            return {"items": [mail(2)], "next_cursor": None}
        self.first_page_reads += 1
        return {
            "items": [mail(1)] if self.first_page_reads == 1 else [],
            "next_cursor": "next-page" if self.first_page_reads == 1 else None,
        }

    def detail(self, mail_id):
        if mail_id not in {"mail-1", "mail-2"}:
            return None
        return {
            **mail(int(mail_id[-1])),
            "to": [{"addr": SESSION["email"], "name": ""}],
            "cc": [],
            "body_text": f'합성 본문 {mail_id}\n<img src="https://outside.invalid/image"><script>bad()</script>',
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--token-file", required=True)
    args = parser.parse_args()
    application = create_app()
    application.state.mail_api = MailAPIContext(
        Path(args.token_file).read_text().strip(), SyntheticRepository()
    )
    uvicorn.run(
        application,
        host="127.0.0.1",
        port=args.port,
        access_log=False,
        proxy_headers=False,
        log_level="error",
    )
