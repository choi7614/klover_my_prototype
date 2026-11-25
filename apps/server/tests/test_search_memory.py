"""불완전한 기억 검색. 실제 모델 정확도가 아닌 합성 계약·실패 경계 검사다."""

import asyncio
import json
from datetime import date

import pytest
from search_support import (
    SCOPE,
    SyntheticAnswerer,
    SyntheticHistory,
    SyntheticParser,
    SyntheticRepository,
    mail,
)
from test_search_ai_adapter import ScriptedGeneration

from app.ai.interfaces import ProviderIdentity, ProvidersNotConfigured
from app.ai.search_adapter import SharedQueryParser
from app.ai.search_semantic import LocalSemanticSearch
from app.schemas.search import ParsedQuery, ParseOutput, SearchRequest
from app.services.search import SearchService
from app.services.search_rules import normalize_intent


@pytest.mark.parametrize(
    "today,period,expected",
    [
        (date(2026, 11, 25), {"month": 10, "part": "early"}, ("2026-10-01", "2026-10-11")),
        (date(2026, 1, 2), {"month": 10, "part": "early"}, ("2025-10-01", "2025-10-11")),
        (
            date(2026, 11, 25),
            {"year": 2024, "month": 2, "part": "late"},
            ("2024-02-21", "2024-03-01"),
        ),
        (date(2026, 11, 25), {"month": 11, "part": "middle"}, ("2026-11-11", "2026-11-21")),
    ],
)
def test_month_parts_are_deterministic(today, period, expected):
    parsed = normalize_intent(ParseOutput(filters={"period": period}, topic="매매"), today)
    assert (str(parsed.filters.period.start), str(parsed.filters.period.end_before)) == expected


@pytest.mark.parametrize(
    "query,topic,expansions,subjects",
    [
        (
            "고속트레이딩 문의",
            "고속트레이딩",
            ["HFT", "고빈도 매매", "초단타 매매", "High-Frequency Trading"],
            ["HFT 문의", "고빈도 매매 검토", "초단타 매매", "High-Frequency Trading"],
        ),
        (
            "싱글사인온 관련 메일",
            "싱글사인온",
            ["SSO", "Single Sign-On"],
            ["SSO 문의", "Single Sign-On 연동"],
        ),
        (
            "장애 복구 문의",
            "장애 복구",
            ["재해 복구", "Disaster Recovery"],
            ["재해 복구 점검", "Disaster Recovery"],
        ),
        ("문서 AB-1042", "AB-1042", [], ["AB-1042 문의"]),
    ],
)
def test_general_expansion_keeps_original_and_excludes_unrelated(
    query, topic, expansions, subjects
):
    generator = ScriptedGeneration(
        json.dumps(
            {"filters": {}, "topic": topic, "original_terms": [topic], "expansions": expansions},
            ensure_ascii=False,
        )
    )
    rows = [
        mail(str(i), subject=subject, body_text="합성 문의") for i, subject in enumerate(subjects)
    ]
    rows.extend(
        [
            mail("original", subject=topic),
            mail("unrelated", subject="무관한 점심", body_text="합성"),
            mail("foreign", subject=topic, account_id="other-account"),
        ]
    )
    target = SearchService(
        SyntheticRepository(rows),
        SyntheticHistory(),
        parser=SharedQueryParser(generator, allow_test_provider=True),
        answerer=SyntheticAnswerer(),
    )
    result = asyncio.run(target.search(SearchRequest(query=query), SCOPE))
    assert {row.mail_id for row in result.results} == {
        "original",
        *(str(i) for i in range(len(subjects))),
    }
    assert result.parsed.original_terms == [topic]
    assert not result.semantic_enabled


def test_unknown_sender_is_not_converted_to_a_name_and_bad_originals_are_retried():
    good = {"filters": {}, "topic": "고속트레이딩", "original_terms": ["고속트레이딩"]}
    bad = {**good, "filters": {"counterparty": {"kind": "name", "value": "모름"}}}
    generator = ScriptedGeneration(json.dumps(bad), json.dumps(good))
    parsed = asyncio.run(
        SharedQueryParser(generator, allow_test_provider=True).parse(
            query="누가 보낸진 모르겠고 고속트레이딩 문의", reference_date=date(2026, 11, 25)
        )
    )
    assert parsed.filters.counterparty is None and len(generator.requests) == 2
    generator = ScriptedGeneration(
        json.dumps({**good, "original_terms": ["엉뚱한 단어"]}), json.dumps(good)
    )
    asyncio.run(
        SharedQueryParser(generator, allow_test_provider=True).parse(
            query="고속트레이딩", reference_date=date(2026, 11, 25)
        )
    )
    assert len(generator.requests) == 2


@pytest.mark.parametrize("failure", ["exception", "timeout", "cancel"])
def test_semantic_failure_timeout_fallback_but_cancel_propagates(failure):
    class Semantic:
        ready = True

        async def search(self, **_):
            if failure == "timeout":
                await asyncio.sleep(1)
            if failure == "cancel":
                raise asyncio.CancelledError
            raise RuntimeError("private-query-and-key-must-not-escape")

    target = SearchService(
        SyntheticRepository(),
        SyntheticHistory(),
        parser=SyntheticParser(),
        answerer=SyntheticAnswerer(),
        semantic=Semantic(),
        model_timeout=0.01,
        clock=lambda: date(2026, 11, 25),
    )
    if failure == "cancel":
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(target.search(SearchRequest(query="예산"), SCOPE))
    else:
        result = asyncio.run(target.search(SearchRequest(query="예산"), SCOPE))
        assert len(result.results) == 3 and not result.semantic_enabled
        assert result.search_warnings[0].code == "semantic_failed"
        assert "private-query" not in result.model_dump_json()


class Embedding:
    identity = ProviderIdentity(provider="ollama", model="synthetic-3d", mode="test")
    external_transfer = False
    dimensions = 3

    def __init__(self, vector):
        self.vector, self.calls = vector, []

    async def embed(self, request):
        self.calls.append(request)
        return [self.vector]


@pytest.mark.parametrize("vector", [[1, 0], [0, 0, 0], [float("nan"), 0, 1]])
def test_invalid_query_vectors_never_reach_repository(vector):
    class Repository:
        def search(self, **_):
            raise AssertionError("잘못된 벡터가 DB에 도달함")

    with pytest.raises(ValueError):
        asyncio.run(
            LocalSemanticSearch(Repository(), Embedding(vector), allow_test_provider=True).search(
                scope=SCOPE, parsed=ParsedQuery(topic="주제"), limit=20
            )
        )


def test_test_or_external_embedding_cannot_be_enabled_in_production():
    with pytest.raises(ProvidersNotConfigured):
        LocalSemanticSearch(None, Embedding([1, 0, 0]))


def test_exact_document_number_not_diluted_by_vector_and_expansion():
    from app.schemas.search import RankedHit
    from app.services.search import combine_results

    rows = (mail("right", subject="AB-1042"), mail("wrong", subject="AB-10420"))
    full, _, _ = combine_results(
        scope=SCOPE,
        parsed=ParsedQuery(topic="AB-1042", expansions=["계약"]),
        mails=rows,
        keyword_ids=["wrong", "right"],
        vector_hits=[RankedHit(mail_id="wrong", score=0.99)],
        limit=20,
    )
    assert [row.mail_id for row in full] == ["right"]


def test_answer_input_is_bounded_without_losing_citation_validation():
    class ShortAnswerer(SyntheticAnswerer):
        async def answer(self, **kwargs):
            from app.schemas.search import AnswerDraft

            self.calls.append(kwargs)
            return AnswerDraft(
                sentences=[
                    {"mail_id": row.mail_id, "quote": row.body_text[:100]}
                    for row in kwargs["mails"]
                ]
            )

    answerer = ShortAnswerer()
    rows = [mail(str(i), body_text="예산" + "합성" * 5000) for i in range(20)]
    target = SearchService(
        SyntheticRepository(rows),
        SyntheticHistory(),
        parser=SyntheticParser(),
        answerer=answerer,
        clock=lambda: date(2026, 11, 25),
    )
    result = asyncio.run(target.search(SearchRequest(query="예산"), SCOPE))
    assert result.answer and not result.answer_error
    sent = answerer.calls[0]["mails"]
    assert len(sent) == 8 and all(len(row.body_text) <= 4000 for row in sent)


def test_ambiguous_acronym_is_not_expanded_to_unrelated_meanings():
    # 합성 모델이 확신할 수 없다고 빈 확장을 낸 경우를 확인한다. 실제 모델 평가는 아니다.
    generator = ScriptedGeneration(json.dumps({"filters": {}, "topic": "ABC", "expansions": []}))
    target = SearchService(
        SyntheticRepository(
            [
                mail("exact", subject="ABC 자료"),
                mail("unrelated", subject="다른 용어", body_text="식당 예약"),
            ]
        ),
        SyntheticHistory(),
        parser=SharedQueryParser(generator, allow_test_provider=True),
        answerer=SyntheticAnswerer(),
    )
    result = asyncio.run(target.search(SearchRequest(query="ABC 관련 메일"), SCOPE))
    assert [row.mail_id for row in result.results] == ["exact"]
    assert result.parsed.expansions == []


def test_insufficient_evidence_can_abstain_without_fabricated_citations():
    from app.schemas.search import AnswerDraft

    target = SearchService(
        SyntheticRepository(),
        SyntheticHistory(),
        parser=SyntheticParser(),
        answerer=SyntheticAnswerer(AnswerDraft(sentences=[])),
        clock=lambda: date(2026, 11, 25),
    )
    result = asyncio.run(target.search(SearchRequest(query="예산"), SCOPE))
    assert result.results and result.answer and not result.answer.citations
    assert "근거가 부족" in result.answer.text


def test_semantic_excerpt_must_exist_in_canonical_mail():
    from app.schemas.search import RankedHit
    from app.services.search import combine_results

    canonical = mail(body_text="앞부분 합성 " * 100 + "같은 주제의 다른 표현")
    valid = RankedHit(mail_id="m1", score=0.9, excerpt="같은 주제의 다른 표현")
    args = dict(
        scope=SCOPE, parsed=ParsedQuery(topic="주제"), mails=(canonical,), keyword_ids=[], limit=20
    )
    full, _, _ = combine_results(**args, vector_hits=[valid])
    assert full[0].snippet == valid.excerpt
    full, _, _ = combine_results(
        **args, vector_hits=[valid.model_copy(update={"excerpt": "지어낸 원문"})]
    )
    assert "지어낸 원문" not in full[0].snippet


@pytest.mark.parametrize(
    "expansions", [["문의"], ["request"], ["가" * 201], [str(n) for n in range(9)]]
)
def test_overbroad_or_oversized_expansions_do_not_succeed(expansions):
    from app.services.search_ports import ModelOutputInvalid

    generator = ScriptedGeneration(
        json.dumps({"filters": {}, "topic": "예산", "expansions": expansions})
    )
    with pytest.raises(ModelOutputInvalid):
        asyncio.run(
            SharedQueryParser(generator, allow_test_provider=True).parse(
                query="예산 문의", reference_date=date(2026, 11, 25)
            )
        )
    assert len(generator.requests) == 2


def test_expansion_and_answer_reuse_selected_ai_and_single_shared_fallback(tmp_path):
    from types import SimpleNamespace

    from test_ai_selection import settings, update

    from app.ai.interfaces import ProviderCallError
    from app.ai.search_adapter import SharedSearchAnswerer
    from app.ai.selection import Defaults, SelectedGeneration, execution_info, selected

    store = settings(tmp_path)
    update(store, defaults=Defaults(search="claude"))
    calls = []

    def loader(values):
        chosen = values["AI_PROVIDER"]

        async def generate(request):
            calls.append(chosen)
            if chosen == "claude":
                raise ProviderCallError(code="claude_unreachable")
            payload = json.loads(request.user_prompt)
            if "mails" not in payload:
                assert set(payload) == {"query", "reference_date"}
                return json.dumps(
                    {
                        "filters": {},
                        "topic": "고속트레이딩",
                        "original_terms": ["고속트레이딩"],
                        "expansions": ["HFT"],
                    }
                )
            return json.dumps(
                {
                    "sentences": [
                        {"mail_id": row["mail_id"], "quote": row["body_text"]}
                        for row in payload["mails"]
                    ]
                }
            )

        return SimpleNamespace(generate=generate)

    generator = SelectedGeneration(store, loader=loader)
    target = SearchService(
        SyntheticRepository([mail("hft", subject="HFT 문의")]),
        SyntheticHistory(),
        parser=SharedQueryParser(generator),
        answerer=SharedSearchAnswerer(generator),
    )

    async def run():
        with selected(store):
            response = await target.search(SearchRequest(query="고속트레이딩 문의"), SCOPE)
            trace = execution_info()
        assert response.answer and response.results[0].mail_id == "hft"
        assert trace["fallback"] and [call["used"] for call in trace["calls"]] == [
            "ollama",
            "ollama",
        ]

    asyncio.run(run())
    assert calls == ["claude", "ollama", "ollama"]


def test_model_cannot_silently_widen_early_month_to_whole_month():
    bad = {
        "filters": {"period": {"start": "2026-10-01", "end_before": "2026-11-01"}},
        "topic": "예산",
    }
    good = {"filters": {"period": {"month": 10, "part": "early"}}, "topic": "예산"}
    provider = ScriptedGeneration(json.dumps(bad), json.dumps(good))
    output = asyncio.run(
        SharedQueryParser(provider, allow_test_provider=True).parse(
            query="10월 초 예산 문의", reference_date=date(2026, 11, 25)
        )
    )
    parsed = normalize_intent(output, date(2026, 11, 25))
    assert str(parsed.filters.period.end_before) == "2026-10-11"
    assert len(provider.requests) == 2
