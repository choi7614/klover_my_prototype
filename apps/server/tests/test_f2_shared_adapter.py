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
    assert common_request.response_schema["title"] == "GeneratedDraft"
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
