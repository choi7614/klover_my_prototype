"""분석·검증·한 번의 재시도. 원문과 외부 오류를 로그에 남기지 않는다."""

import asyncio
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.ai.interfaces import GenerationRequest, TextGeneration
from app.pipeline.analysis_diagnostics import (
    Reason,
    provider_reason,
    record_failure,
    repair_hint,
    schema_reason,
)
from app.schemas.mail_analysis import AnalysisMail, AnalysisResult, CategoryExample

PROMPT = Path(__file__).resolve().parents[1] / "ai/prompts/analyze.md"


class AnalysisFailed(Exception):
    def __init__(self, code: str, attempts: int, *, reason: Reason | None = None):
        self.code = code
        self.attempts = attempts
        self.reason = reason
        super().__init__(code)


async def analyze(
    mail: AnalysisMail,
    provider: TextGeneration,
    examples: tuple[CategoryExample, ...] = (),
    *,
    timeout: float = 20,
) -> tuple[AnalysisResult, int]:
    if len(mail.body_text) > 200_000:
        record_failure(Reason.INPUT_SIZE, 0)
        raise AnalysisFailed("input_too_large", 0, reason=Reason.INPUT_SIZE)
    payload = {
        "mail": mail.model_dump(mode="json", exclude={"user_id", "account_id", "source"}),
        "reference_date": mail.received_at.astimezone(ZoneInfo("Asia/Seoul")).date().isoformat(),
        "timezone": "Asia/Seoul",
        "body_text_length": len(mail.body_text),
        "category_examples": [example.model_dump() for example in examples],
    }
    for attempt in (1, 2):
        request = GenerationRequest(
            purpose="analysis",
            system_prompt=PROMPT.read_text(encoding="utf-8"),
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_schema=AnalysisResult.model_json_schema(),
        )
        try:
            raw = await asyncio.wait_for(provider.generate(request), timeout)
        except Exception as error:
            reason = provider_reason(error)
            record_failure(reason, attempt)
            raise AnalysisFailed("provider_error", attempt, reason=reason) from None
        reason = None
        if not isinstance(raw, str) or len(raw) > 200_000:
            reason = Reason.SIZE
        else:
            try:
                result = AnalysisResult.model_validate_json(raw, strict=True)
            except ValidationError as error:
                reason = schema_reason(error)
            else:
                if result.mail_id != mail.mail_id:
                    reason = Reason.MAIL_ID
                elif any(span.end > len(mail.body_text) for span in result.evidence_spans):
                    reason = Reason.EVIDENCE
                else:
                    try:
                        result.check_source(mail)
                    except ValueError:
                        reason = Reason.SOURCE
                    else:
                        return result, attempt
        record_failure(reason, attempt)
        if attempt == 2:
            raise AnalysisFailed("invalid_response", attempt, reason=reason) from None
        payload["retry_reason"] = "invalid_response"
        payload["repair_instruction"] = repair_hint(reason)
    raise AssertionError("도달할 수 없는 분석 경로")
