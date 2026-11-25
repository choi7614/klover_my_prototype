"""실제 AI 없이 F1 공통 계약 재사용과 테스트 제공자의 운영 차단을 확인한다."""

import asyncio
import json
from datetime import UTC, datetime

import pytest

from app.ai.f2_port import F2Error
from app.ai.f2_shared_adapter import SharedDraftAI
from app.ai.interfaces import ProviderCallError, ProviderIdentity, ProvidersNotConfigured
from app.schemas.profile_draft import DraftMail, GenerationInput, Profile


class SharedSyntheticGeneration:
    identity = ProviderIdentity(provider="f2-test-double", model="synthetic-json", mode="test")

    def __init__(self, response=None):
        self.requests = []
        self.response = response

    async def generate(self, request):
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response or json.dumps(
            {
                "body": "합성 검사 문장입니다.",
                "directions": ["확인 후 회신", "추가 문의"],
                "selected_direction": "확인 후 회신",
                "evidence": [],
            },
            ensure_ascii=False,
        )


def input_for(purpose="draft"):
    return GenerationInput(
        purpose=purpose,
        profile=Profile(name="합성 사용자"),
        original=DraftMail(
            mail_id="synthetic-only",
            subject="합성 제목",
            body_text="합성 본문",
            from_addr="synthetic@example.invalid",
            received_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )


@pytest.mark.parametrize("purpose", ["draft", "preview"])
def test_common_generation_contract_is_used_with_f2_schema(purpose):
    generator = SharedSyntheticGeneration()
    adapter = SharedDraftAI(generator, allow_test_provider=True)
    result = asyncio.run(adapter.generate(input_for(purpose)))
    assert result.body == "합성 검사 문장입니다."
    common_request = generator.requests[0]
    assert common_request.purpose == "draft"
    assert json.loads(common_request.user_prompt)["purpose"] == purpose
    assert json.loads(common_request.user_prompt)["original"]["mail_id"] == "synthetic-only"
    assert common_request.response_schema["title"] == "DraftOutput"
    assert "신뢰할 수 없는 데이터" in common_request.system_prompt


def test_test_provider_is_rejected_without_explicit_test_opt_in():
    with pytest.raises(F2Error) as error:
        SharedDraftAI(SharedSyntheticGeneration())
    assert error.value.code == "ai_unavailable"


@pytest.mark.parametrize(
    "failure,code,status",
    [
        (ProvidersNotConfigured("synthetic-private"), "ai_unavailable", 503),
        (ProviderCallError("synthetic-private"), "ai_failed", 502),
        (ProviderCallError("synthetic-private", code="ollama_timeout"), "ai_timeout", 504),
        (ProviderCallError("synthetic-private", code="claude_timeout"), "ai_timeout", 504),
        ("invalid-json-synthetic-private", "invalid_ai_output", 502),
    ],
)
def test_common_provider_failure_is_explicit_and_does_not_echo_output(failure, code, status):
    adapter = SharedDraftAI(SharedSyntheticGeneration(failure), allow_test_provider=True)
    with pytest.raises(F2Error) as error:
        asyncio.run(adapter.generate(input_for()))
    assert error.value.code == code and error.value.status == status
    assert "synthetic-private" not in str(error.value) + error.value.message


def test_reply_author_and_recipient_are_distinct_even_for_first_person_incoming_mail():
    request = input_for().model_copy(
        update={
            "profile": Profile(name="합성 수신 담당자", org="합성 공급사"),
            "original": input_for().original.model_copy(
                update={"from_name": "합성 문의자", "body_text": "저는 고객입니다. 자료를 주세요."}
            ),
        }
    )
    generator = SharedSyntheticGeneration()
    asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(request))
    payload = json.loads(generator.requests[0].user_prompt)
    assert payload["reply_context"] == {
        "task": "reply_to_sender",
        "author": {"name": "합성 수신 담당자", "org": "합성 공급사"},
        "recipient": {"name": "합성 문의자", "address": "synthetic@example.invalid"},
    }
    assert payload["original"]["body_text"] == request.original.body_text
    assert request.profile.name == "합성 수신 담당자"


@pytest.mark.parametrize("body", ["합성 본문", "  합성\n본문  "])
def test_incoming_mail_echo_is_rejected_without_exposing_content(body):
    response = json.dumps(
        {
            "body": body,
            "directions": ["요청 확인", "추가 문의"],
            "selected_direction": "요청 확인",
            "evidence": [],
        }
    )
    adapter = SharedDraftAI(SharedSyntheticGeneration(response), allow_test_provider=True)
    with pytest.raises(F2Error) as error:
        asyncio.run(adapter.generate(input_for()))
    assert error.value.code == "invalid_ai_output"
    assert "합성" not in error.value.message


@pytest.mark.parametrize("label", ["shorter", "politer", "REWRITE"])
def test_edit_action_codes_are_rejected_as_reply_directions(label):
    response = json.dumps(
        {
            "body": "자료 요청을 확인했습니다.",
            "directions": [label, "추가 문의"],
            "selected_direction": label,
            "evidence": [],
        }
    )
    adapter = SharedDraftAI(SharedSyntheticGeneration(response), allow_test_provider=True)
    with pytest.raises(F2Error) as error:
        asyncio.run(adapter.generate(input_for()))
    assert error.value.code == "invalid_ai_output"


def test_revision_keeps_user_reply_and_action_separate_from_incoming_mail():
    request = input_for().model_copy(
        update={
            "action": "shorter",
            "direction": "추가 문의",
            "current_body": "대상 기간을 알려 주세요.",
        }
    )
    response = json.dumps(
        {
            "body": "기간을 알려 주세요.",
            "directions": ["요청 확인", "추가 문의"],
            "selected_direction": "추가 문의",
            "evidence": [],
        }
    )
    generator = SharedSyntheticGeneration(response)
    result = asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(request))
    payload = json.loads(generator.requests[0].user_prompt)
    assert payload["action"] == "shorter"
    assert payload["direction"] == "추가 문의"
    assert payload["current_body"] == "대상 기간을 알려 주세요."
    assert result.body == "기간을 알려 주세요."


MAIL_TEXT = "3분기 부서별 예산 집행 현황 자료를 금요일까지 보내 주세요."


@pytest.mark.parametrize("greeting,closing", [("", ""), ("안녕하세요.", "감사합니다.")])
def test_evidence_is_computed_by_server_with_or_without_fixed_profile_parts(greeting, closing):
    from app.services.profile_draft import compose

    request = input_for().model_copy(
        update={
            "profile": Profile(name="합성 사용자", greeting=greeting, closing=closing),
            "original": input_for().original.model_copy(update={"body_text": MAIL_TEXT}),
        }
    )
    reply = "요청하신 3분기 부서별 예산 집행 현황 자료는 확인 후 공유드리겠습니다."
    generator = SharedSyntheticGeneration(
        json.dumps(
            {
                "body": "😀 " + reply,
                "directions": ["확인 후 회신", "추가 문의"],
                "selected_direction": "확인 후 회신",
            },
            ensure_ascii=False,
        )
    )
    result = asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(request))
    # 문장 단위로 표시한다(이모지 같은 앞머리도 그 문장에 포함).
    assert result.evidence[0].span == (0, len(result.body))
    body, evidence = compose(result, request)
    item = next(e for e in evidence if e.source.startswith("mail:"))
    assert item.source == "mail:synthetic-only"
    assert body[item.span[0] : item.span[1]] == "😀 " + reply
    assert len(generator.requests) == 1


@pytest.mark.parametrize(
    "garbage",
    [
        {"source": "mail:other-owner", "text": "x", "source_quote": "y"},
        {"source": "profile.greeting", "text": "검사 문장", "source_quote": "합성 본문"},
        {
            "text": "본문에 없는 문구",
            "source": "mail:synthetic-only",
            "source_quote": "원문에 없는 비밀",
        },
        "not-an-object",
        [1, 2, 3],
    ],
)
def test_model_supplied_evidence_is_ignored_and_never_makes_the_draft_fail(garbage):
    generator = SharedSyntheticGeneration(
        json.dumps(
            {
                "body": "검사 문장",
                "directions": ["확인", "문의"],
                "selected_direction": "확인",
                "evidence": [garbage],
            }
        )
    )
    result = asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(input_for()))
    # 모델이 낸 근거는 쓰지 않는다. 다른 사람 메일·인사말 같은 출처가 결과에 섞이지 않는다.
    assert result.body == "검사 문장" and result.evidence == ()
    assert len(generator.requests) == 1
    assert "evidence" not in generator.requests[0].response_schema["properties"]


def test_bad_output_has_one_repair_attempt_without_echoing_response():
    class Repair(SharedSyntheticGeneration):
        async def generate(self, request):
            if not self.requests:
                self.requests.append(request)
                return "synthetic-private-invalid-response"
            return await super().generate(request)

    generator = Repair()
    result = asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(input_for()))
    assert result.body == "합성 검사 문장입니다."
    assert len(generator.requests) == 2
    assert "synthetic-private-invalid-response" not in generator.requests[-1].user_prompt
