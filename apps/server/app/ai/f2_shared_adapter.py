"""F1 공통 텍스트 생성 계약을 F2 포트로 연결한다. 실제 제공자를 구현하지 않는다."""

import json
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
        try:
            raw = await self.generator.generate(
                GenerationRequest(
                    purpose="draft",
                    system_prompt=prompt,
                    user_prompt=json.dumps(payload, ensure_ascii=False),
                    response_schema=GeneratedDraft.model_json_schema(),
                )
            )
        except ProvidersNotConfigured:
            raise F2Error("ai_unavailable", 503, "AI 연결이 준비되지 않았어요.") from None
        except ProviderCallError as error:
            if error.code in {"ollama_timeout", "claude_timeout"}:
                raise F2Error(
                    "ai_timeout", 504, "AI 응답이 늦어졌어요. 잠시 뒤 다시 시도해 주세요."
                ) from None
            raise F2Error("ai_failed", 502, "초안을 만들지 못했어요. 다시 시도해 주세요.") from None
        try:
            result = GeneratedDraft.model_validate_json(raw)
            # 수정 버튼 코드와 답장 방향은 다른 개념이다. 잘못된 결과를 저장하지 않는다.
            if any(
                direction.casefold() in {"shorter", "politer", "rewrite"}
                for direction in result.directions
            ):
                raise ValueError("답장 방향 대신 수정 코드 반환")
            if "".join(result.body.split()) == "".join(request.original.body_text.split()):
                raise ValueError("답장 대신 원문 그대로 반환")
            return result
        except (ValidationError, ValueError, TypeError):
            raise F2Error("invalid_ai_output", 502, "AI 결과 형식을 확인하지 못했어요.") from None
