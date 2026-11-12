from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.report import ReportMail


class FixtureMailFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    synthetic: Literal[True]
    mails: tuple[ReportMail, ...]


def load_fixture_mails(path: Path) -> tuple[ReportMail, ...]:
    """호출자가 명시한 가짜 메일 파일만 읽는다. 외부 메일 서비스에는 접근하지 않는다."""
    return FixtureMailFile.model_validate_json(path.read_text(encoding="utf-8")).mails
