"""명시적으로 실행하는 받은편지함 동기화. 성공한 배치의 커서만 전진한다."""

import math
from datetime import UTC, datetime, timedelta

from app.connectors.gmail_mail import GmailStatusError, identifier
from app.connectors.gmail_message import parse_message, received_at
from app.google_config import GoogleConnectionError

MAX_PAGES = 100
MAX_MESSAGES = 10000


def _access_token(repository, client):
    refreshed = False
    with repository.credentials() as credential:
        tokens = credential.tokens
        if datetime.fromisoformat(tokens["expires_at"]) <= datetime.now(UTC) + timedelta(
            seconds=60
        ):
            tokens = client.refresh(tokens)
            refreshed = True
        credential.tokens = tokens
        access = tokens["access_token"]
    # 갱신 결과는 프로필·메일 요청보다 먼저 확정해 회전된 refresh token도 잃지 않는다.
    if not refreshed:
        try:
            client.profile(access)
        except GmailStatusError as error:
            if error.status != 401:
                raise
            with repository.credentials() as credential:
                current = credential.tokens
                if current["access_token"] == access:
                    current = client.refresh(current)
                    refreshed = True
                credential.tokens = current
                access = current["access_token"]
    return access, refreshed


def _pages(client, path, access, params):
    token, seen = None, set()
    for _ in range(MAX_PAGES):
        current = dict(params)
        if token:
            current["pageToken"] = token
        page = client.get(path, access, current)
        yield page
        token = page.get("nextPageToken")
        if not token:
            return
        if not isinstance(token, str) or len(token) > 4096 or token in seen:
            raise GoogleConnectionError("Gmail 페이지 정보를 확인하지 못했습니다")
        seen.add(token)
    raise GoogleConnectionError("조회 상한에 도달했습니다. 기존 데이터와 커서는 보존됩니다")


def _initial_ids(client, access, start, label="INBOX"):
    params = {
        "q": f"after:{math.floor(start.timestamp()) - 1}",
        "labelIds": label,
        "maxResults": 100,
        "fields": "messages/id,nextPageToken",
    }
    for page in _pages(client, "/messages", access, params):
        messages = page.get("messages", [])
        if not isinstance(messages, list):
            raise GoogleConnectionError("메일 목록 형식을 확인하지 못했습니다")
        for message in messages:
            yield identifier(message.get("id"))


def _history_ids(client, access, cursor):
    params = {
        "startHistoryId": cursor,
        "historyTypes": ["messageAdded", "labelAdded"],
        "labelId": "INBOX",
        "maxResults": 100,
    }
    for page in _pages(client, "/history", access, params):
        history = page.get("history", [])
        if not isinstance(history, list):
            raise GoogleConnectionError("메일 변경 이력을 확인하지 못했습니다")
        for record in history:
            for field in ["messagesAdded", "labelsAdded"]:
                changes = record.get(field, [])
                if not isinstance(changes, list):
                    raise GoogleConnectionError("메일 변경 이력을 확인하지 못했습니다")
                for change in changes:
                    yield identifier(change["message"]["id"])


def synchronize(repository, client):
    access, refreshed = _access_token(repository, client)
    with repository.batch() as batch:
        baseline = client.profile(access)
        mode = "history" if batch.cursor else "initial"
        ids = (
            _history_ids(client, access, batch.cursor)
            if batch.cursor
            else _initial_ids(client, access, batch.start)
        )
        stats = {"saved": 0, "skipped": 0, "mode": mode, "token_refreshed": refreshed}
        seen = set()

        def collect(source_ids, label="INBOX"):
            # 받은 메일(INBOX)은 받은편지함, 보낸 메일(SENT)은 보낸편지함에 저장한다.
            sent = label == "SENT"
            for source_id in source_ids:
                if source_id in seen:
                    continue
                seen.add(source_id)
                if len(seen) > MAX_MESSAGES:
                    raise GoogleConnectionError(
                        "메일 개수 제한에 도달했습니다. 기존 데이터는 보존됩니다"
                    )
                if batch.contains(source_id):
                    if not sent:
                        stats["skipped"] += 1
                    continue
                path = "/messages/" + source_id
                try:
                    meta = client.get(
                        path, access, {"format": "metadata", "fields": "id,internalDate,labelIds"}
                    )
                    if meta.get("id") != source_id:
                        raise GoogleConnectionError("메일 식별자를 확인하지 못했습니다")
                    if received_at(meta) < batch.start or label not in meta.get("labelIds", []):
                        if not sent:
                            stats["skipped"] += 1
                        continue
                    message = client.get(
                        path,
                        access,
                        {"format": "full", "fields": "id,threadId,internalDate,labelIds,payload"},
                    )
                except GmailStatusError as error:
                    if error.status != 404:
                        raise
                    if not sent:
                        stats["skipped"] += 1
                    continue
                mail = parse_message(message)
                if mail.source_id != source_id:
                    raise GoogleConnectionError("메일 식별자를 확인하지 못했습니다")
                if mail.received_at < batch.start or label not in message.get("labelIds", []):
                    if not sent:
                        stats["skipped"] += 1
                    continue
                if sent:
                    # 보낸 메일은 보기만 한다. 건수(saved)는 새로 받은 메일만 센다.
                    batch.store_sent(mail)
                else:
                    batch.store(mail)
                    stats["saved"] += 1

        try:
            collect(ids)
        except GmailStatusError as error:
            if error.status != 404 or not batch.cursor:
                raise
            stats["mode"] = "rescan"
            collect(_initial_ids(client, access, batch.start))
        # 보낸 메일은 변경 이력 대신 사용 시작 이후 목록을 매번 훑는다.
        # 이미 저장한 메일은 본문을 다시 받지 않고, 이 기능 이전에 연결한 계정도 저절로 채워진다.
        collect(_initial_ids(client, access, batch.start, "SENT"), "SENT")
        batch.advance(baseline)
    return stats
