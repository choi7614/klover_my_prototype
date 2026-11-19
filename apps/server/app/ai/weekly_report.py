import json
from pathlib import Path
from typing import Literal, Protocol

from app.ai.interfaces import GenerationRequest, ProvidersNotConfigured, TextGeneration
from app.schemas.report import WeeklyReportInput
from app.schemas.weekly_report import GeneratedReport, ReportProfile


class WeeklyReportGenerator(Protocol):
    mode: Literal["test_double", "ai"]

    async def generate(
        self, *, source: WeeklyReportInput, profile: ReportProfile, style: str, recipient: str
    ) -> GeneratedReport:
        """공통 TextGeneration 어댑터 또는 명시적 검사 대역을 받는다."""
        ...


class SharedWeeklyReportGenerator:
    """공통 AI 계약으로만 호출한다. 제공자 SDK·키·가짜 기본 응답을 만들지 않는다."""

    def __init__(self, generator: TextGeneration, *, allow_test_provider: bool = False):
        if generator.identity.mode != "live" and not allow_test_provider:
            raise ProvidersNotConfigured("주간 보고의 실제 AI 제공자가 아직 연결되지 않았습니다")
        self.generator = generator
        self.mode: Literal["test_double", "ai"] = (
            "test_double" if generator.identity.mode == "test" else "ai"
        )

    async def generate(self, *, source, profile, style, recipient):
        prompt = (Path(__file__).parent / "prompts/weekly_report.md").read_text(encoding="utf-8")
        # 제외된 메일은 외부 호출 입력에 포함하지 않는다.
        payload = {
            "period": source.period.model_dump(mode="json"),
            "profile": profile.model_dump(mode="json", exclude={"user_id"}),
            "style": style,
            "recipient": recipient,
            "groups": [
                {
                    "group_id": group.group_id,
                    "mail_ids": group.mail_ids,
                    "mails": [
                        mail.model_dump(mode="json", exclude={"user_id"}) for mail in group.mails
                    ],
                }
                for group in source.groups
            ],
        }
        raw = await self.generator.generate(
            GenerationRequest(
                purpose="weekly_report",
                system_prompt=prompt,
                user_prompt=json.dumps(payload, ensure_ascii=False),
                response_schema=GeneratedReport.model_json_schema(),
            )
        )
        return GeneratedReport.model_validate_json(raw)
