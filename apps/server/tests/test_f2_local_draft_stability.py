"""합성 응답으로 로컬 초안 검증의 오거절·진단·편집본 보존을 재현한다. 외부 호출 없음."""

import asyncio
import json
import logging

import pytest
from test_f2_generation_timeout import service
from test_f2_shared_adapter import SharedSyntheticGeneration, input_for

from app.ai.f2_port import F2Error
from app.ai.f2_shared_adapter import SharedDraftAI
from app.ai.interfaces import ProviderCallError
from app.schemas.profile_draft import DraftCreate, DraftRevise, Profile


def output(**changes):
    return {
        "body": "요청을 확인했습니다.",
        "directions": ["확인 후 회신", "추가 문의"],
        "selected_direction": "확인 후 회신",
        "evidence": [],
        **changes,
    }


def quote(**changes):
    return {
        "text": "요청을 확인했습니다.",
        "source": "mail:synthetic-only",
        "source_quote": "합성 본문",
        **changes,
    }


def adapter(response):
    generator = SharedSyntheticGeneration(
        response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
    )
    return SharedDraftAI(generator, allow_test_provider=True), generator


@pytest.mark.parametrize("fixed", [False, True])
def test_repeated_exact_text_gets_distinct_nonoverlapping_verified_spans(fixed):
    from app.services.profile_draft import compose

    request = input_for().model_copy(
        update={
            "profile": Profile(
                greeting="안녕하세요." if fixed else "",
                closing="감사합니다." if fixed else "",
            )
        }
    )
    target, generator = adapter(
        output(
            body="요청을 확인했습니다.\n확인할 내용:\n요청을 확인했습니다.",
            evidence=[quote(), quote()],
        )
    )
    result = asyncio.run(target.generate(request))
    assert len(generator.requests) == 1
    assert len(result.evidence) == 2
    first, second = result.evidence
    assert first.span[1] <= second.span[0]
    body, evidence = compose(result, request)
    for item in evidence:
        if item.source.startswith("mail:"):
            assert body[item.span[0] : item.span[1]] == "요청을 확인했습니다."


@pytest.mark.parametrize(
    "response,reason",
    [
        ("private-response-canary invalid JSON", "json_invalid"),
        (output(extra_private_field="private-response-canary"), "schema_invalid"),
        (output(body="  "), "body_or_directions_invalid"),
        (output(selected_direction="private-direction-canary"), "body_or_directions_invalid"),
        (output(evidence=[quote(text="private-quote-canary")]), "body_quote_missing"),
        (output(evidence=[quote(source="mail:private-id-canary")]), "source_not_allowed"),
        (output(evidence=[quote(source_quote="private-source-canary")]), "source_quote_missing"),
        (output(evidence=[quote(source="profile.greeting")]), "schema_invalid"),
        (output(evidence=[quote(), quote()]), "evidence_overlap"),
        (output(body="합성 본문"), "incoming_echo"),
        (
            output(directions=["shorter", "추가 문의"], selected_direction="shorter"),
            "edit_code_as_direction",
        ),
    ],
)
def test_failure_reasons_are_fixed_and_do_not_log_or_echo_private_values(response, reason, caplog):
    target, generator = adapter(response)
    request = input_for().model_copy(update={"profile": Profile(name="private-profile-canary")})
    with caplog.at_level(logging.WARNING):
        with pytest.raises(F2Error) as error:
            asyncio.run(target.generate(request))
    assert error.value.code == "invalid_ai_output"
    assert getattr(error.value, "reason", None) == reason
    assert len(generator.requests) == 2
    assert f"reason={reason}" in caplog.text
    assert "private-" not in caplog.text + error.value.message
    repair = json.loads(generator.requests[1].user_prompt)["previous_attempt_error"]
    assert reason in repair and "private-" not in repair


def test_specific_repair_hint_recovers_without_discarding_valid_evidence():
    class Repair(SharedSyntheticGeneration):
        async def generate(self, request):
            self.requests.append(request)
            return json.dumps(
                output(
                    evidence=[
                        quote(source_quote="없는 인용") if len(self.requests) == 1 else quote()
                    ]
                ),
                ensure_ascii=False,
            )

    generator = Repair()
    result = asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(input_for()))
    assert len(generator.requests) == 2 and len(result.evidence) == 1
    repair = json.loads(generator.requests[1].user_prompt)["previous_attempt_error"]
    assert "source_quote_missing" in repair and "없는 인용" not in repair


@pytest.mark.parametrize("operation", ["create", "revise"])
def test_rejected_output_never_saves_or_replaces_draft_profile_or_user_edit(operation):
    target, _ = adapter(output(evidence=[quote(source_quote="없는 인용")]))
    api, repository = service(target)
    previous, profile = repository.previous.model_dump(), repository.profile().model_dump()
    request = (
        api.create(DraftCreate(mail_id="synthetic-only"))
        if operation == "create"
        else api.revise(
            "draft-old", DraftRevise(body="보존할 새 편집", expected_version=1, action="rewrite")
        )
    )
    with pytest.raises(F2Error):
        asyncio.run(request)
    assert repository.saved == []
    assert repository.previous.model_dump() == previous
    assert repository.profile().model_dump() == profile


@pytest.mark.parametrize(
    "change,response,reason",
    [
        ({"direction": "추가 문의"}, output(), "direction_mismatch"),
        (
            {"profile": Profile(excluded_phrases=("확인",))},
            output(),
            "excluded_phrase",
        ),
        (
            {},
            output(evidence=[quote(source="profile.phrase", source_quote="요청을 확인했습니다.")]),
            "learned_phrase_mismatch",
        ),
        ({"purpose": "preview"}, output(evidence=[quote()]), "source_not_allowed"),
    ],
)
def test_request_specific_guards_remain_strict_and_diagnosable(change, response, reason):
    target, generator = adapter(response)
    with pytest.raises(F2Error) as error:
        asyncio.run(target.generate(input_for().model_copy(update=change)))
    assert error.value.reason == reason and len(generator.requests) == 2


def test_source_quote_whitespace_is_not_guessed_or_normalized_to_a_different_quote():
    target, _ = adapter(output(evidence=[quote(source_quote="합성\n본문")]))
    with pytest.raises(F2Error) as error:
        asyncio.run(target.generate(input_for()))
    assert error.value.reason == "source_quote_missing"


@pytest.mark.parametrize(
    "code,safe_reason,error_code",
    [
        ("ollama_model_not_found", "ollama_model_not_found", "ai_failed"),
        ("ollama_unreachable", "ollama_unreachable", "ai_failed"),
        ("ollama_invalid_response", "ollama_invalid_response", "ai_failed"),
        ("ollama_timeout", "ollama_timeout", "ai_timeout"),
        ("private-error-code-canary", "provider_failed", "ai_failed"),
    ],
)
def test_provider_failures_use_only_fixed_diagnostics_without_format_retry(
    code, safe_reason, error_code, caplog
):
    generator = SharedSyntheticGeneration(
        ProviderCallError("private-key-response-canary", code=code)
    )
    with caplog.at_level(logging.WARNING), pytest.raises(F2Error) as error:
        asyncio.run(SharedDraftAI(generator, allow_test_provider=True).generate(input_for()))
    assert error.value.code == error_code and len(generator.requests) == 1
    assert f"reason={safe_reason}" in caplog.text
    assert "private-" not in caplog.text + error.value.message


@pytest.mark.parametrize("stop", ["deadline", "cancel"])
def test_repair_does_not_reset_deadline_or_swallow_cancellation(monkeypatch, stop):
    class SlowRepair(SharedSyntheticGeneration):
        def __init__(self):
            super().__init__()
            self.entered = asyncio.Event()
            self.cancelled = False

        async def generate(self, request):
            self.requests.append(request)
            if len(self.requests) == 1:
                return "invalid-json"
            self.entered.set()
            try:
                await asyncio.Future()
            finally:
                self.cancelled = True

    from app.services import profile_draft

    monkeypatch.setattr(profile_draft, "AI_TIMEOUT_SECONDS", 0.05 if stop == "deadline" else 120)

    async def scenario():
        generator = SlowRepair()
        target = SharedDraftAI(generator, allow_test_provider=True)
        api, repository = service(target)
        task = asyncio.create_task(
            api.revise(
                "draft-old", DraftRevise(body="편집본 유지", expected_version=1, action="rewrite")
            )
        )
        await asyncio.wait_for(generator.entered.wait(), timeout=1)
        if stop == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(F2Error) as error:
                await task
            assert error.value.code == "ai_timeout"
        assert generator.cancelled and len(generator.requests) == 2
        assert repository.saved == [] and repository.previous.body == "사용자가 편집한 본문"

    asyncio.run(scenario())
