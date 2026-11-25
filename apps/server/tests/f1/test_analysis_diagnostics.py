"""합성 응답으로 F1 실패 구분·보정·비밀 정보 비기록을 확인한다. 모델 품질 검사가 아니다."""

import asyncio
import json

import pytest

from app.ai.interfaces import ProviderCallError
from app.pipeline.analyze import AnalysisFailed, analyze
from tests.f1.support import CASES, ScriptedGeneration, sample_mail


@pytest.mark.parametrize(
    "override,reason",
    [
        ({"category": "업무 요청"}, "category_invalid"),
        ({"summary": "첫 줄\n둘째 줄\n셋째 줄"}, "summary_invalid"),
        ({"needs_reply": "true"}, "schema_invalid"),
        ({"action_items": [{"text": "자료 요청", "due": "금요일"}]}, "actions_invalid"),
        (
            {
                "events": [
                    {"title": "회의", "start": "2026-11-20T09:00:00", "end": None, "location": None}
                ]
            },
            "events_invalid",
        ),
        ({"evidence_spans": [{"kind": "action", "start": 0, "end": 999999}]}, "evidence_invalid"),
        ({"evidence_spans": [{"kind": "action", "start": 2, "end": 1}]}, "evidence_invalid"),
        ({"mail_id": "private-other-mail-id"}, "mail_id_mismatch"),
        ({"private-extra-key": "private-value"}, "schema_extra"),
    ],
)
def test_invalid_output_keeps_rejection_and_has_fixed_repair_hint(override, reason, caplog):
    response = json.dumps({**CASES[0]["expected"], **override})
    provider = ScriptedGeneration([response, response])
    with pytest.raises(AnalysisFailed) as caught:
        asyncio.run(analyze(sample_mail(), provider))
    assert caught.value.code == "invalid_response"  # 기존 저장·API 코드 보존
    assert caught.value.reason == reason
    assert caught.value.attempts == 2
    assert len(provider.calls) == 2
    retry = json.loads(provider.calls[1].user_prompt)
    assert retry["retry_reason"] == "invalid_response"
    assert reason in retry["repair_instruction"]
    assert "생략" in retry["repair_instruction"]
    assert f"F1 analysis rejected reason={reason} attempt=2" in caplog.text
    for secret in (
        "private-extra-key",
        "private-value",
        "private-other-mail-id",
        sample_mail().body_text,
        sample_mail().mail_id,
    ):
        assert secret not in caplog.text
    assert "private-extra-key" not in provider.calls[1].user_prompt
    assert "private-other-mail-id" not in provider.calls[1].user_prompt


@pytest.mark.parametrize(
    "raw,reason",
    [
        ('{"private-key": "private-value"', "json_invalid"),
        ('{"private-key": "private-value"}', "schema_missing"),
        (None, "response_size_or_type"),
        ("x" * 200001, "response_size_or_type"),
    ],
)
def test_bad_response_can_be_repaired_once_without_echoing_raw_output(raw, reason, caplog):
    provider = ScriptedGeneration([raw, json.dumps(CASES[0]["expected"])])
    result, attempts = asyncio.run(analyze(sample_mail(), provider))
    assert result.model_dump(mode="json") == CASES[0]["expected"]
    assert attempts == 2
    retry = json.loads(provider.calls[1].user_prompt)
    assert reason in retry["repair_instruction"]
    assert "private-key" not in provider.calls[1].user_prompt
    assert "private-value" not in caplog.text
    assert f"reason={reason} attempt=1" in caplog.text


@pytest.mark.parametrize(
    "error,reason",
    [
        (ProviderCallError("private-token", code="ollama_timeout"), "ollama_timeout"),
        (ProviderCallError("private-token", code="private-model-error"), "provider_failed"),
        (RuntimeError("private-token"), "provider_failed"),
    ],
)
def test_provider_errors_are_allowlisted_and_not_schema_retried(error, reason, caplog):
    provider = ScriptedGeneration([error])
    with pytest.raises(AnalysisFailed) as caught:
        asyncio.run(analyze(sample_mail(), provider))
    assert caught.value.code == "provider_error"
    assert caught.value.reason == reason
    assert len(provider.calls) == 1
    assert f"reason={reason}" in caplog.text
    assert "private-token" not in caplog.text
    assert "private-model-error" not in caplog.text


def test_timeout_is_distinct_and_cancellation_propagates(caplog):
    class Hanging(ScriptedGeneration):
        async def generate(self, request):
            await asyncio.Future()

    with pytest.raises(AnalysisFailed) as caught:
        asyncio.run(analyze(sample_mail(), Hanging(), timeout=0.001))
    assert caught.value.reason == "timeout"

    async def cancel():
        task = asyncio.create_task(analyze(sample_mail(), Hanging()))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    assert "reason=timeout" in caplog.text


def test_initial_prompt_includes_exact_body_length_and_contract_guidance():
    provider = ScriptedGeneration()
    asyncio.run(analyze(sample_mail(), provider))
    payload = json.loads(provider.calls[0].user_prompt)
    assert payload["body_text_length"] == len(sample_mail().body_text)
    assert "repair_instruction" not in payload
    assert "필수 항목" in provider.calls[0].system_prompt
