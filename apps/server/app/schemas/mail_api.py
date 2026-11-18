"""앱이 읽는 메일 계약. HTML 원문·OAuth 토큰은 포함하지 않는다."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel


class MailContact(BaseModel):
    addr: str
    name: str = ""


class MailSummary(BaseModel):
    mail_id: str
    subject: str
    from_addr: str
    from_name: str
    preview: str
    received_at: AwareDatetime
    is_read: bool
    analysis_status: Literal["pending", "done", "failed"]


class MailDetail(MailSummary):
    to: list[MailContact]
    cc: list[MailContact]
    body_text: str


class MailPage(BaseModel):
    items: list[MailSummary]
    next_cursor: str | None


class LocalSession(BaseModel):
    user_id: str
    account_id: str
    email: str
    sync_started_at: AwareDatetime
