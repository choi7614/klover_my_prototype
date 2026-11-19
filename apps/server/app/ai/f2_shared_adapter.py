"""F1 공통 텍스트 생성 계약을 F2 포트로 연결한다. 실제 제공자를 구현하지 않는다."""

from pathlib import Path

from pydantic import ValidationError

from app.ai.f2_port import F2Error
from app.ai.interfaces import (
    GenerationRequest,
    ProviderCallError,
    ProvidersNotConfigured,
    TextGeneration,
)
from app.schemas.profile_draft import GeneratedDraft, GenerationInput


class SharedDraftAI:
    def __init__(self, generator: TextGeneration, *, allow_test_provider: bool = False):
        if generator.identity.mode != "live" and not allow_test_provider:
            raise F2Error("ai_unavailable", 503, "운영 AI 제공자가 아직 연결되지 않았어요.")
        self.generator = generator

    async def generate(self, request: GenerationInput) -> GeneratedDraft:
        prompt = (Path(__file__).parent / "prompts/draft.md").read_text(encoding="utf-8")
        try:
            raw = await self.generator.generate(
                GenerationRequest(
                    purpose="draft",
                    system_prompt=prompt,
                    user_prompt=request.model_dump_json(),
                    response_schema=GeneratedDraft.model_json_schema(),
                )
            )
        except ProvidersNotConfigured:
            raise F2Error("ai_unavailable", 503, "AI 연결이 준비되지 않았어요.") from None
        except ProviderCallError:
            raise F2Error("ai_failed", 502, "초안을 만들지 못했어요. 다시 시도해 주세요.") from None
        try:
            return GeneratedDraft.model_validate_json(raw)
        except (ValidationError, TypeError):
            raise F2Error("invalid_ai_output", 502, "AI 결과 형식을 확인하지 못했어요.") from None
