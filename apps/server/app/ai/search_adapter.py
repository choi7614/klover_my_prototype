"""F1 공통 텍스트 생성 계약을 F3 검색 포트로 연결한다.

제공자(Claude·로컬 LLM)는 직접 고르지 않는다.
"""

import json
import re
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.ai.interfaces import GenerationRequest, ProvidersNotConfigured, TextGeneration
from app.schemas.search import AnswerDraft, ParsedQuery, ParseOutput, SearchMail
from app.services.search_ports import ModelOutputInvalid

PROMPTS = Path(__file__).parent / "prompts"
# 형식을 어기기 쉬운 로컬 모델을 위해 한 번만 다시 묻는다.
# 전체 대기 시간은 SearchService의 model_timeout이 제한한다.
MAX_ATTEMPTS = 2
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _strip_fence(raw: str) -> str:
    text = raw.strip()
    match = _FENCE.match(text)
    return match.group(1) if match else text


def _require_live(generator: TextGeneration, allow_test_provider: bool) -> None:
    if generator.identity.mode != "live" and not allow_test_provider:
        raise ProvidersNotConfigured("검색의 실제 AI 제공자가 아직 연결되지 않았습니다")


async def _generate_valid[T: BaseModel](
    generator: TextGeneration,
    *,
    prompt_file: str,
    payload: dict,
    model: type[T],
    check: Callable[[T], None] = lambda _: None,
) -> T:
    """형식 오류면 오류 종류만 알려 주고 재시도한다. 제공자 오류·시간 초과는 재시도하지 않는다."""
    system_prompt = (PROMPTS / prompt_file).read_text(encoding="utf-8")
    user_prompt = json.dumps(payload, ensure_ascii=False)
    for _ in range(MAX_ATTEMPTS):
        raw = await generator.generate(
            GenerationRequest(
                purpose="search",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=model.model_json_schema(),
            )
        )
        try:
            if not isinstance(raw, str):
                raise TypeError("문자열 응답이 아닙니다")
            result = model.model_validate_json(_strip_fence(raw))
            check(result)
            return result
        except (ValidationError, ValueError, TypeError):
            # 모델 응답 원문은 다시 보내지 않는다(본문 유출·프롬프트 주입 방지).
            user_prompt = json.dumps(
                {
                    **payload,
                    "previous_attempt_error": (
                        "직전 응답이 출력 규칙을 지키지 않았습니다. "
                        "스키마에 맞는 JSON 객체 하나만 다시 출력하세요."
                    ),
                },
                ensure_ascii=False,
            )
    raise ModelOutputInvalid("모델 응답이 검색 계약 형식을 지키지 않았습니다")


class SharedQueryParser:
    def __init__(self, generator: TextGeneration, *, allow_test_provider: bool = False):
        _require_live(generator, allow_test_provider)
        self.generator = generator

    async def parse(self, *, query: str, reference_date: date) -> ParseOutput:
        # 질문과 기준 날짜만 보낸다. 메일 원문·사용자 식별 정보는 넣지 않는다.
        return await _generate_valid(
            self.generator,
            prompt_file="search_parse.md",
            payload={"query": query, "reference_date": reference_date.isoformat()},
            model=ParseOutput,
        )


class SharedSearchAnswerer:
    def __init__(self, generator: TextGeneration, *, allow_test_provider: bool = False):
        _require_live(generator, allow_test_provider)
        self.generator = generator

    async def answer(
        self, *, query: str, parsed: ParsedQuery, mails: Sequence[SearchMail]
    ) -> AnswerDraft:
        allowed = {mail.mail_id: mail for mail in mails}

        def quotes_exist(draft: AnswerDraft) -> None:
            # 서버의 validate_answer와 같은 기준으로 미리 확인해, 틀리면 한 번 다시 묻는다.
            for sentence in draft.sentences:
                mail = allowed.get(sentence.mail_id)
                if mail is None or not any(
                    sentence.quote in part for part in (mail.subject, mail.body_text)
                ):
                    raise ValueError("근거 인용을 확인하지 못했습니다")

        return await _generate_valid(
            self.generator,
            prompt_file="search_answer.md",
            payload={
                "query": query,
                "parsed": parsed.model_dump(mode="json"),
                "mails": [
                    mail.model_dump(
                        mode="json",
                        include={"mail_id", "subject", "body_text", "from_name", "received_at"},
                    )
                    for mail in mails
                ],
            },
            model=AnswerDraft,
            check=quotes_exist,
        )
