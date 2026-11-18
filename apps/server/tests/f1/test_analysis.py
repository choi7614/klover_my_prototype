import asyncio
import json
from datetime import date
from typing import get_args

import pytest
from pydantic import ValidationError

from app.ai.interfaces import ProviderCallError
from app.pipeline.analyze import AnalysisFailed, analyze
from app.pipeline.embed import EmbeddingFailed, body_chunks, embed_mail, validate_vectors
from app.schemas.mail_analysis import AnalysisResult
from app.schemas.report import MailCategory
from tests.f1.support import CASES, DATASET, ScriptedEmbedding, ScriptedGeneration, sample_mail


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_golden_contract_and_stub_round_trip(case):
    # 정답을 되돌리는 대역의 계약 검사이며 모델 정답률을 계산하는 검사가 아니다.
    result, attempts = asyncio.run(
        analyze(sample_mail(CASES.index(case)), ScriptedGeneration([json.dumps(case["expected"])]))
    )
    assert result.model_dump(mode="json") == case["expected"]
    assert attempts == 1


def test_dataset_is_synthetic_diverse_and_documents_dates():
    assert DATASET["synthetic"] is True
    assert len(CASES) >= 20
    assert len({case["case_id"] for case in CASES}) == len(CASES)
    assert {case["expected"]["category"] for case in CASES} == set(get_args(MailCategory))
    assert CASES[0]["expected"]["action_items"][0]["due"] == "2026-11-20"
    assert CASES[-2]["expected"]["action_items"][0]["due"] == "2027-01-01"
    for case in CASES:
        assert case["rubric"]["category_reason"]
        assert case["mail"]["from_addr"].endswith(".invalid")


@pytest.mark.parametrize(
    "override",
    [
        {"category": "업무 요청"},
        {"category": "custom"},
        {"needs_reply": "yes"},
        {"needs_reply": 1},
        {"summary": "a\nb\nc"},
        {"priority": "urgent"},
        {"mail_id": "other-user-mail"},
        {"extra": "ignored?"},
        {"action_items": [{"text": "자료", "due": "이번 주 금요일"}]},
        {"action_items": [{"text": "자료", "due": "2026-02-30"}]},
        {"action_items": [{"text": "자료", "due": 123456789}]},
        {"action_items": [{"text": "자료", "due": "20261120"}]},
        {"evidence_spans": [{"kind": "due", "start": 0, "end": 1000000}]},
        {"evidence_spans": [{"kind": "due", "start": True, "end": 2}]},
        {"entities": {"projects": [123], "orgs": [], "people": []}},
        {
            "events": [
                {"title": "회의", "start": "2026-11-20T09:00:00", "end": None, "location": None}
            ]
        },
        {
            "events": [
                {
                    "title": "회의",
                    "start": "2026-11-20T10:00:00+09:00",
                    "end": "2026-11-20T09:00:00+09:00",
                    "location": None,
                }
            ]
        },
    ],
)
def test_invalid_contract_retries_only_once(override):
    response = json.dumps({**CASES[0]["expected"], **override})
    llm = ScriptedGeneration([response, response, json.dumps(CASES[0]["expected"])])
    with pytest.raises(AnalysisFailed) as caught:
        asyncio.run(analyze(sample_mail(), llm))
    assert caught.value.code == "invalid_response"
    assert caught.value.attempts == 2
    assert len(llm.calls) == 2
    assert json.loads(llm.calls[1].user_prompt)["retry_reason"] == "invalid_response"


def test_valid_response_after_one_retry_and_no_raw_error_in_prompt():
    llm = ScriptedGeneration(
        ['{"secret_external_response": "do not repeat"}', json.dumps(CASES[0]["expected"])]
    )
    result, attempts = asyncio.run(analyze(sample_mail(), llm))
    assert result.category == "work_request"
    assert result.action_items[0].due == date(2026, 11, 20)
    assert attempts == 2
    assert "secret_external_response" not in llm.calls[1].user_prompt


def test_missing_field_is_not_silently_defaulted():
    response = dict(CASES[0]["expected"])
    del response["events"]
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate_json(json.dumps(response), strict=True)


def test_provider_error_is_sanitized_and_not_schema_retried():
    llm = ScriptedGeneration([ProviderCallError("external-private-content")])
    with pytest.raises(AnalysisFailed) as caught:
        asyncio.run(analyze(sample_mail(), llm))
    assert str(caught.value) == "provider_error"
    assert caught.value.attempts == 1


def test_timeout_is_bounded():
    class Hanging(ScriptedGeneration):
        async def generate(self, request):
            await asyncio.Future()

    with pytest.raises(AnalysisFailed, match="provider_error"):
        asyncio.run(analyze(sample_mail(), Hanging(), timeout=0.001))


def test_seoul_reference_date_and_untrusted_mail_in_user_payload():
    mail = sample_mail(22)
    llm = ScriptedGeneration()
    asyncio.run(analyze(mail, llm))
    payload = json.loads(llm.calls[0].user_prompt)
    assert payload["reference_date"] == "2026-11-19"
    assert payload["timezone"] == "Asia/Seoul"
    assert mail.body_text not in llm.calls[0].system_prompt
    assert "user_id" not in payload["mail"]


def test_unicode_evidence_and_paragraph_chunks_keep_all_content():
    text = "한글 요청\n\n" + "자료" * 2000
    chunks = body_chunks(text)
    assert all(0 < len(chunk) <= 1200 for chunk in chunks)
    assert "".join(chunks) == text.replace("\n\n", "")
    response = {
        **CASES[0]["expected"],
        "evidence_spans": [{"kind": "action", "start": 0, "end": 5}],
    }
    result, _ = asyncio.run(analyze(sample_mail(), ScriptedGeneration([json.dumps(response)])))
    assert result.evidence_spans[0].end == 5


@pytest.mark.parametrize(
    "vectors,dimensions,count",
    [
        ([], 3, 1),
        ([[1, 2]], 3, 1),
        ([[float("nan"), 1, 2]], 3, 1),
        ([[float("inf"), 1, 2]], 3, 1),
        ([[0, 0, 0]], 3, 1),
        ([[True, 1, 2]], 3, 1),
        ([["1", 1, 2]], 3, 1),
        ([[1e100, 1, 2]], 3, 1),
        ([[1e-100, 0, 0]], 3, 1),
        ([[1, 2, 3]], True, 1),
    ],
)
def test_invalid_vectors_rejected(vectors, dimensions, count):
    with pytest.raises(ValueError):
        validate_vectors(vectors, dimensions=dimensions, count=count)


def test_body_and_summary_separate_and_empty_body_is_supported():
    provider = ScriptedEmbedding()
    chunks = asyncio.run(embed_mail("단락1\n\n단락2", "요약", provider))
    assert [(c.kind, c.seq) for c in chunks] == [("body", 0), ("body", 1), ("summary", 0)]
    assert provider.calls[0].texts == ("단락1", "단락2", "요약")
    assert len(asyncio.run(embed_mail("", "요약", provider))) == 1


def test_embedding_provider_failure_does_not_make_fake_vectors():
    with pytest.raises(EmbeddingFailed, match="embedding_error"):
        asyncio.run(embed_mail("원문", "요약", ScriptedEmbedding(RuntimeError("private"))))
