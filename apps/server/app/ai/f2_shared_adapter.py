"""F1 공통 텍스트 생성 계약을 F2 포트로 연결한다. 실제 제공자를 구현하지 않는다."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.f2_port import F2Error
from app.ai.interfaces import (
    GenerationRequest,
    ProviderCallError,
    ProvidersNotConfigured,
    TextGeneration,
)
from app.ai.json_output import clean_json_text
from app.schemas.profile_draft import Evidence, GeneratedDraft, GenerationInput


class DraftQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str = Field(min_length=1, max_length=20000)
    source: str = Field(pattern=r"^(profile\.phrase|mail:[A-Za-z0-9_-]{1,128})$")
    source_quote: str = Field(min_length=1, max_length=20000)


class QuotedDraft(GeneratedDraft):
    evidence: tuple[DraftQuote, ...] = Field(default=(), max_length=100)


def grounded_draft(raw: str, request: GenerationInput) -> GeneratedDraft:
    quoted = QuotedDraft.model_validate_json(clean_json_text(raw))
    mails = {m.mail_id: m for m in (request.original, *request.related)}
    evidence = []
    for item in quoted.evidence:
        start = quoted.body.find(item.text)
        if start < 0:
            raise ValueError("본문 인용 불일치")
        if item.source == "profile.phrase":
            if item.text != item.source_quote or item.text not in request.learned_phrases:
                raise ValueError("학습 표현 불일치")
        else:
            mail = mails.get(item.source[5:])
            if (
                request.purpose == "preview"
                or mail is None
                or not any(item.source_quote in value for value in (mail.body_text, mail.subject))
            ):
                raise ValueError("원문 인용 불일치")
        evidence.append(Evidence(span=(start, start + len(item.text)), source=item.source))
    evidence.sort(key=lambda e: e.span)
    result = GeneratedDraft(**quoted.model_dump(exclude={"evidence"}), evidence=tuple(evidence))
    if request.direction is not None and result.selected_direction != request.direction:
        raise ValueError("선택 방향 불일치")
    if any(phrase in result.body for phrase in request.profile.excluded_phrases):
        raise ValueError("제외 표현 포함")
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
        for _attempt in range(2):
            try:
                raw = await self.generator.generate(
                    GenerationRequest(
                        purpose="draft",
                        system_prompt=prompt,
                        user_prompt=json.dumps(payload, ensure_ascii=False),
                        response_schema=QuotedDraft.model_json_schema(),
                    )
                )
            except ProvidersNotConfigured:
                raise F2Error("ai_unavailable", 503, "AI 연결이 준비되지 않았어요.") from None
            except ProviderCallError as error:
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
                    "ai_failed", 502, "초안을 만들지 못했어요. 다시 시도해 주세요."
                ) from None
            try:
                result = grounded_draft(raw, request)
                if any(
                    direction.casefold() in {"shorter", "politer", "rewrite"}
                    for direction in result.directions
                ):
                    raise ValueError("답장 방향 대신 수정 코드 반환")
                if "".join(result.body.split()) == "".join(request.original.body_text.split()):
                    raise ValueError("답장 대신 원문 그대로 반환")
                return result
            except (ValidationError, ValueError, TypeError, F2Error):
                # 잘못된 원문 응답은 다시 보내거나 로그에 남기지 않는다.
                payload["previous_attempt_error"] = (
                    "본문·근거·선택 방향 검증에 실패했습니다. "
                    "스키마에 맞는 JSON과 정확한 인용을 반환하세요."
                )
        raise F2Error(
            "invalid_ai_output", 502, "AI 결과의 본문과 근거를 확인하지 못했어요."
        ) from None
