"""F1 공통 텍스트 생성 계약을 F2 포트로 연결한다. 실제 제공자를 구현하지 않는다."""

import json
from pathlib import Path

from pydantic import ValidationError

from app.ai.f2_evidence import derive_evidence
from app.ai.f2_output_diagnostics import (
    InvalidDraftOutput,
    OutputReason,
    record_provider_failure,
    record_rejection,
    repair_hint,
    schema_reason,
)
from app.ai.f2_port import F2Error
from app.ai.interfaces import (
    GenerationRequest,
    ProviderCallError,
    ProvidersNotConfigured,
    TextGeneration,
)
from app.ai.json_output import clean_json_text
from app.schemas.profile_draft import DraftCore, GeneratedDraft, GenerationInput


class DraftOutput(DraftCore):
    """제공자에게 요구하는 응답 형식. 근거 문구는 요구하지 않는다(서버가 계산)."""


def grounded_draft(raw: str, request: GenerationInput) -> GeneratedDraft:
    if not isinstance(raw, str):
        raise InvalidDraftOutput(OutputReason.SCHEMA_INVALID)
    try:
        data = json.loads(clean_json_text(raw))
    except ValueError:
        raise InvalidDraftOutput(OutputReason.JSON_INVALID) from None
    if not isinstance(data, dict):
        raise InvalidDraftOutput(OutputReason.SCHEMA_INVALID)
    # 예전 형식을 따라 근거(evidence)를 같이 보낸 모델도 실패시키지 않는다. 내용은 쓰지 않고 버린다.
    data.pop("evidence", None)
    try:
        output = DraftOutput.model_validate(data)
    except ValidationError as error:
        raise InvalidDraftOutput(schema_reason(error)) from None
    result = GeneratedDraft(**output.model_dump(), evidence=derive_evidence(output.body, request))
    if request.direction is not None and result.selected_direction != request.direction:
        raise InvalidDraftOutput(OutputReason.DIRECTION)
    if any(phrase in result.body for phrase in request.profile.excluded_phrases):
        raise InvalidDraftOutput(OutputReason.EXCLUDED_PHRASE)
    from app.services.profile_draft import compose

    compose(result, request)
    return result


class SharedDraftAI:
    def __init__(self, generator: TextGeneration, *, allow_test_provider: bool = False):
        if generator.identity.mode != "live" and not allow_test_provider:
            raise F2Error("ai_unavailable", 503, "운영 AI 제공자가 아직 연결되지 않았어요.")
        self.generator = generator

    async def generate(self, request: GenerationInput) -> GeneratedDraft:
        prompt = (Path(__file__).parent / "prompts/draft.md").read_text(encoding="utf-8")
        payload = request.model_dump(mode="json")
        # 원문 발신자를 작성자로 오해하지 않도록 두 역할을 명시한다.
        payload["reply_context"] = {
            "task": "reply_to_sender",
            "author": {"name": request.profile.name, "org": request.profile.org},
            "recipient": {
                "name": request.original.from_name,
                "address": request.original.from_addr,
            },
        }
        operation = (
            "preview" if request.purpose == "preview" else "revise" if request.action else "create"
        )
        last_reason = OutputReason.VALIDATION
        for _attempt in range(2):
            try:
                raw = await self.generator.generate(
                    GenerationRequest(
                        purpose="draft",
                        system_prompt=prompt,
                        user_prompt=json.dumps(payload, ensure_ascii=False),
                        response_schema=DraftOutput.model_json_schema(),
                    )
                )
            except ProvidersNotConfigured:
                record_provider_failure("provider_not_configured", operation=operation)
                raise F2Error("ai_unavailable", 503, "AI 연결이 준비되지 않았어요.") from None
            except ProviderCallError as error:
                label = record_provider_failure(error.code, operation=operation)
                if error.code == "both_providers_failed":
                    raise F2Error(
                        "both_providers_failed",
                        502,
                        "Claude와 로컬 AI 모두 처리하지 못했어요. 편집 내용은 보존됩니다.",
                    ) from None
                if error.code in {"ollama_timeout", "claude_timeout"}:
                    raise F2Error(
                        "ai_timeout", 504, "AI 응답이 늦어졌어요. 잠시 뒤 다시 시도해 주세요."
                    ) from None
                raise F2Error(
                    "ai_failed", 502, f"초안을 만들지 못했어요. ({label}) 다시 시도해 주세요."
                ) from None
            try:
                result = grounded_draft(raw, request)
                if any(
                    direction.casefold() in {"shorter", "politer", "rewrite"}
                    for direction in result.directions
                ):
                    raise InvalidDraftOutput(OutputReason.EDIT_CODE)
                if "".join(result.body.split()) == "".join(request.original.body_text.split()):
                    raise InvalidDraftOutput(OutputReason.INCOMING_ECHO)
                return result
            except (ValidationError, ValueError, TypeError, F2Error) as error:
                # 잘못된 원문 응답은 다시 보내거나 로그에 남기지 않는다.
                last_reason = (
                    error.reason
                    if isinstance(error, InvalidDraftOutput)
                    else schema_reason(error)
                    if isinstance(error, ValidationError)
                    else OutputReason.VALIDATION
                )
                record_rejection(last_reason, attempt=_attempt + 1, operation=operation)
                payload["previous_attempt_error"] = repair_hint(last_reason)
        raise InvalidDraftOutput(last_reason) from None
