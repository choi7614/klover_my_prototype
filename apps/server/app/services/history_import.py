"""작은 페이지 단위의 수동 과거 INBOX 가져오기. 실제 연결은 실행 조립부에서만 주입한다."""

import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.connectors.gmail_mail import GmailStatusError, identifier
from app.connectors.gmail_message import parse_message
from app.services.gmail_sync import _access_token

ZONE = ZoneInfo("Asia/Seoul")


class HistoryRunner:
    def __init__(self, repository, sync_repository, client_factory, after_save=lambda: None):
        self.repository, self.sync_repository, self.client_factory, self.after_save = (
            repository,
            sync_repository,
            client_factory,
            after_save,
        )
        self.lock = threading.Lock()
        self.threads = {}
        self.repository.recover()

    def resume(self, job_id):
        with self.lock:
            if job_id in self.threads and self.threads[job_id].is_alive():
                raise ValueError("busy")
            data = self.repository.transition(job_id, "resume")
            if data is None:
                return None
            worker = threading.Thread(
                target=self.run, args=(job_id, data["run_id"]), daemon=True, name="gmail-history"
            )
            self.threads[job_id] = worker
            worker.start()
            return data

    def run(self, job_id, run_id=None):
        initial = self.repository.get(job_id)
        if initial is None:
            return
        run_id = run_id or initial.get("run_id")

        def checkpoint(**kwargs):
            return self.repository.checkpoint(job_id, expected_run_id=run_id, **kwargs)

        try:
            with self.client_factory() as client:
                access, _ = _access_token(self.sync_repository, client)
                while True:
                    data = self.repository.get(job_id)
                    if not data or (data["status"] != "running" or data.get("run_id") != run_id):
                        return
                    if data["processed"] >= 10000 or data["pages"] >= 1000:
                        checkpoint(failure="range_limit")
                        return
                    start = datetime.combine(
                        datetime.fromisoformat(data["start"]).date(), time.min, tzinfo=ZONE
                    )
                    end = datetime.combine(
                        datetime.fromisoformat(data["end"]).date() + timedelta(days=1),
                        time.min,
                        tzinfo=ZONE,
                    )
                    params = {
                        "q": f"after:{int(start.timestamp()) - 1} before:{int(end.timestamp())}",
                        "labelIds": "INBOX",
                        "maxResults": 25,
                        "fields": "messages/id,nextPageToken",
                    }
                    if data["page_token"]:
                        params["pageToken"] = data["page_token"]
                    access, _ = _access_token(self.sync_repository, client)
                    try:
                        page = client.get("/messages", access, params)
                    except GmailStatusError as error:
                        if error.status == 400 and data["page_token"]:
                            checkpoint(failure="page_expired")
                            return
                        raise
                    messages = page.get("messages", [])
                    if not isinstance(messages, list) or len(messages) > 25:
                        raise ValueError("invalid_page")
                    for item in messages:
                        current = self.repository.get(job_id)
                        if not current or (
                            current["status"] != "running" or current.get("run_id") != run_id
                        ):
                            return
                        if current["processed"] >= 10000:
                            checkpoint(failure="range_limit")
                            return
                        source_id = identifier(item.get("id"))
                        if source_id in current["page_done"]:
                            continue
                        raw = client.get("/messages/" + source_id, access, {"format": "full"})
                        message = parse_message(raw)
                        if not start <= message.received_at < end or "INBOX" not in raw.get(
                            "labelIds", []
                        ):
                            message = None
                        if not checkpoint(source_id=source_id, message=message):
                            return
                        self.after_save()
                    token = page.get("nextPageToken")
                    if token is not None and (
                        not isinstance(token, str)
                        or len(token) > 4096
                        or token == data["page_token"]
                    ):
                        raise ValueError("invalid_page")
                    if not checkpoint(page_token=token, page_end=True):
                        return
                    self.after_save()
                    if not token:
                        return
        except Exception:
            # 키·본문·외부 예외 상세는 보관하지 않는다.
            checkpoint(failure="import_failed")
