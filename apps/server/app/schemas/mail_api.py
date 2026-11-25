"""앱이 읽는 메일 계약. HTML 원문·OAuth 토큰은 포함하지 않는다."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel

from app.schemas.report import MailCategory


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
    # 보낸 메일 목록에서 받는 사람을 보여 주기 위한 값. 받은 메일은 비어 있다.
    direction: Literal["received", "sent"] = "received"
    to_label: str = ""


class MailDetail(MailSummary):
    to: list[MailContact]
    cc: list[MailContact]
    body_text: str


class MailPage(BaseModel):
    items: list[MailSummary]
    next_cursor: str | None


class MailCategoryCounts(BaseModel):
    """받은편지함 분류별 메일 수. 분석이 안 끝난 메일은 total에만 들어간다."""

    total: int
    counts: dict[MailCategory, int]


class LocalSession(BaseModel):
    user_id: str
    account_id: str
    email: str
    sync_started_at: AwareDatetime


class MailSyncResult(BaseModel):
    """Gmail 새 받은 메일 가져오기 결과. 메일 내용·토큰은 포함하지 않는다."""

    saved: int
    skipped: int
    mode: Literal["initial", "history", "rescan"]
    token_refreshed: bool
