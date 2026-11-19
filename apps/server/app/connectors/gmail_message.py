"""Gmail MIME 응답을 최소 메일 저장 모델로 해석한다. HTML은 실행·보관하지 않는다."""

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses
from html.parser import HTMLParser

from app.connectors.gmail_mail import identifier
from app.google_config import GoogleConnectionError


@dataclass(repr=False)
class ReceivedMail:
    source_id: str
    received_at: datetime
    thread_id: str | None
    from_addr: str = field(repr=False)
    from_name: str = field(repr=False)
    to: list[dict] = field(repr=False)
    cc: list[dict] = field(repr=False)
    subject: str = field(repr=False)
    body_text: str = field(repr=False)
    is_read: bool


def received_at(message):
    value = message.get("internalDate")
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or len(value) > 16:
        raise GoogleConnectionError("메일 수신 시각을 확인하지 못했습니다")
    try:
        return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=int(value))
    except (ValueError, OverflowError):
        raise GoogleConnectionError("메일 수신 시각을 확인하지 못했습니다") from None


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"br", "p", "div", "li"} and not self.hidden:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif tag in {"p", "div", "li"} and not self.hidden:
            self.text.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def _headers(part):
    result = {}
    values = part.get("headers", [])
    if not isinstance(values, list):
        raise ValueError
    for value in values:
        name, text = value["name"], value["value"]
        if not isinstance(name, str) or not isinstance(text, str):
            raise ValueError
        name = name.lower()
        result[name] = result.get(name, "") + (", " if name in result else "") + text
    return result


def _decoded(value):
    return str(make_header(decode_header(value)))


def _contacts(value):
    contacts = getaddresses([_decoded(value)])
    if len(contacts) > 200:
        raise ValueError
    return [{"addr": address, "name": name} for name, address in contacts if address]


def parse_message(message):
    try:
        source_id = identifier(message["id"])
        thread_id = identifier(message["threadId"]) if message.get("threadId") else None
        payload = message["payload"]
        headers = _headers(payload)
        plain, markup, total = [], [], 0
        stack = [(payload, 0)]
        visited = 0
        while stack:
            part, depth = stack.pop()
            visited += 1
            if depth > 30 or visited > 200:
                raise ValueError
            part_headers = _headers(part)
            if (
                part.get("filename")
                or "attachment" in part_headers.get("content-disposition", "").lower()
            ):
                continue
            parts = part.get("parts", [])
            if not isinstance(parts, list):
                raise ValueError
            stack.extend((child, depth + 1) for child in reversed(parts))
            mime = part.get("mimeType", "").lower()
            data = part.get("body", {}).get("data")
            if mime not in {"text/plain", "text/html"} or not data:
                continue
            if not isinstance(data, str) or len(data) > 6 * 1024 * 1024:
                raise ValueError
            raw = base64.b64decode(data + "=" * (-len(data) % 4), altchars=b"-_", validate=True)
            total += len(raw)
            if total > 4 * 1024 * 1024:
                raise ValueError
            content_type = Message()
            content_type["content-type"] = part_headers.get("content-type", mime)
            text = raw.decode(content_type.get_content_charset() or "utf-8", errors="replace")
            (plain if mime == "text/plain" else markup).append(text)
        body = "\n".join(plain)
        if not body.strip() and markup:
            parser = PlainHTML()
            parser.feed("\n".join(markup))
            body = "".join(parser.text).strip()
        sender = _contacts(headers.get("from", ""))
        sender = sender[0] if sender else {"addr": "", "name": ""}
        labels = message.get("labelIds", [])
        if not isinstance(labels, list):
            raise ValueError
        return ReceivedMail(
            source_id,
            received_at(message),
            thread_id,
            sender["addr"],
            sender["name"],
            _contacts(headers.get("to", "")),
            _contacts(headers.get("cc", "")),
            _decoded(headers.get("subject", "")),
            body,
            "UNREAD" not in labels,
        )
    except (ValueError, KeyError, TypeError, AttributeError, LookupError, RecursionError):
        raise GoogleConnectionError(
            "메일 구조를 해석하지 못했습니다. 기존 데이터는 보존됩니다"
        ) from None
