import asyncio

import pytest
from search_support import (
    MAILS,
    SCOPE,
    TODAY,
    SyntheticAnswerer,
    SyntheticHistory,
    SyntheticParser,
    SyntheticRepository,
    mail,
)

from app.schemas.search import ParsedQuery, ParseOutput, RankedHit, SearchRequest
from app.services.search import SearchService, combine_results
from app.services.search_rules import SearchError


def service(**kwargs):
    return SearchService(
        kwargs.pop("repository", SyntheticRepository()),
        kwargs.pop("history", SyntheticHistory()),
        parser=kwargs.pop("parser", SyntheticParser()),
        answerer=kwargs.pop("answerer", SyntheticAnswerer()),
        clock=lambda: TODAY,
        **kwargs,
    )


def search(target, **kwargs):
    return asyncio.run(target.search(SearchRequest(query="지난달 예산 메일", **kwargs), SCOPE))


def test_synthetic_exact_three_results_and_only_result_evidence_in_order():
    answerer = SyntheticAnswerer()
    target = service(answerer=answerer)
    result = search(target)
    assert {row.mail_id for row in result.results} == {"m1", "m2", "m3"}
    assert [row.mail_id for row in result.partial] == ["partial"]
    assert {mail.mail_id for mail in answerer.calls[0]["mails"]} == {"m1", "m2", "m3"}
    assert result.answer and len(result.answer.citations) == 3
    numbers = {row.mail_id: row.number for row in result.results}
    assert all(numbers[cite.mail_id] == cite.number for cite in result.answer.citations)
    assert not result.semantic_enabled
    assert all(row.reason for row in result.results)

    async def events():
        return [event async for event in target.events(SearchRequest(query="예산"), SCOPE)]

    assert [event["type"] for event in asyncio.run(events())] == ["parsed", "results", "answer"]


def test_unavailable_parser_and_empty_or_invalid_output_never_succeed():
    with pytest.raises(SearchError) as error:
        search(service(parser=None))
    assert error.value.code == "parser_unavailable"
    for output in [{"private-token": "not-to-echo"}, {}, {"filters": {}, "topic": None}]:
        with pytest.raises(SearchError) as error:
            search(service(parser=SyntheticParser(output=output)))
        assert error.value.code == "parse_failed" and "private-token" not in str(error.value)


def test_unsupported_organization_and_reply_filter_do_not_become_normal_search():
    output = ParseOutput(filters={"replied": False}, topic="예산")
    with pytest.raises(SearchError) as error:
        search(service(parser=SyntheticParser(output)))
    assert error.value.code == "unsupported_filter"


def test_zero_results_does_not_call_answer_model_even_with_partial_results():
    answerer = SyntheticAnswerer()
    result = search(
        service(
            repository=SyntheticRepository([MAILS[3]]),
            answerer=answerer,
        )
    )
    assert result.results == [] and len(result.partial) == 1
    assert result.answer.text == "찾은 메일이 없습니다" and result.answer.citations == []
    assert answerer.calls == []


@pytest.mark.parametrize(
    "sentence",
    [
        {"mail_id": "foreign", "quote": "다음 분기 예산 재배정을 협의해 주세요."},
        {"mail_id": "partial", "quote": "다음 분기 예산 재배정을 협의해 주세요."},
        {"mail_id": "m1", "quote": "검색 결과에 없는 합성 주장"},
    ],
)
def test_invalid_id_partial_id_or_invented_quote_are_not_returned(sentence):
    result = search(service(answerer=SyntheticAnswerer({"sentences": [sentence]})))
    assert result.results and result.answer is None
    assert result.answer_error.code == "invalid_answer"
    assert "합성 주장" not in result.answer_error.message


def test_answer_port_absence_keeps_results_without_fake_ai_success():
    result = search(service(answerer=None))
    assert len(result.results) == 3 and result.answer is None
    assert result.answer_error.code == "answer_unavailable"


def test_chip_removal_reuses_stored_interpretation_and_clears_topic_expansions():
    parser = SyntheticParser()
    target = service(parser=parser)
    initial = search(target)
    modified = search(target, search_id=initial.search_id, overrides={"period": None})
    assert len(parser.calls) == 1
    assert {row.mail_id for row in modified.results} == {"m1", "m2", "m3", "partial"}
    again = search(target, search_id=modified.search_id, overrides={"topic": None})
    assert again.parsed.filters.period is None and again.parsed.topic is None
    assert again.parsed.expansions == []


def test_history_cannot_be_reused_by_other_user_or_account_or_different_query():
    target = service()
    result = search(target)
    request = SearchRequest(query="지난달 예산 메일", search_id=result.search_id)
    for update in [{"user_id": "foreign"}, {"account_id": "foreign"}]:
        with pytest.raises(SearchError) as error:
            asyncio.run(target.search(request, SCOPE.model_copy(update=update)))
        assert error.value.status == 404
    with pytest.raises(SearchError) as error:
        asyncio.run(target.search(request.model_copy(update={"query": "다른 질문"}), SCOPE))
    assert error.value.code == "invalid_search"


def test_vector_duplicate_chunks_do_not_inflate_rank_and_foreign_ids_do_not_leak():
    class SyntheticVectors:
        ready = True

        async def search(self, **_):
            return [
                RankedHit(mail_id=identifier, score=score)
                for identifier, score in [
                    ("m3", 0.95),
                    ("m3", 0.94),
                    ("m1", 0.90),
                    ("foreign", 0.99),
                    ("old", 0.95),
                    ("partial", 0.85),
                ]
            ]

    result = search(service(semantic=SyntheticVectors()))
    assert result.semantic_enabled  # 합성 포트 검사이며 실제 임베딩 정확도 검사가 아니다.
    assert len({row.mail_id for row in result.results}) == 3
    assert "vector" in result.results[0].sources
    assert "foreign" not in str(result) and "old" not in {row.mail_id for row in result.results}
    assert result.partial[0].missing_conditions == ["기간"]
    assert [row.number for row in result.results] == [1, 2, 3]


def test_semantic_unready_is_not_called_and_vector_only_candidate_is_canonicalized():
    class Unready:
        ready = False

        async def search(self, **_):
            raise AssertionError("준비 전에는 벡터 검색을 호출하면 안 됩니다")

    assert not search(service(semantic=Unready())).semantic_enabled

    class Vectors:
        ready = True

        async def search(self, **_):
            return [{"mail_id": "semantic", "score": 0.9}]

    target = service(
        repository=SyntheticRepository(
            [mail("semantic", subject="비용", body_text="비용 전용 문의")]
        ),
        semantic=Vectors(),
    )
    result = search(target)
    assert [row.mail_id for row in result.results] == ["semantic"]
    assert result.results[0].sources == ["vector"]


def test_model_timeout_and_exception_are_redacted():
    class Slow:
        async def parse(self, **_):
            await asyncio.sleep(0.1)

    with pytest.raises(SearchError) as error:
        search(service(parser=Slow(), model_timeout=0.001))
    assert error.value.code == "parse_unavailable"

    class Broken:
        async def parse(self, **_):
            raise RuntimeError("synthetic-private-content")

    with pytest.raises(SearchError) as error:
        search(service(parser=Broken()))
    assert "synthetic-private" not in str(error.value)


def test_chunk_duplicates_and_out_of_scope_hits_cannot_change_eligible_ranking():
    values = dict(
        scope=SCOPE,
        parsed=ParsedQuery(topic="예산"),
        mails=MAILS,
        keyword_ids=["m1", "m2", "m3"],
        limit=20,
    )
    baseline, _, _ = combine_results(
        **values,
        vector_hits=[
            RankedHit(mail_id="m3", score=0.9),
            RankedHit(mail_id="m1", score=0.8),
        ],
    )
    duplicated, _, _ = combine_results(
        **{**values, "mails": (*MAILS, MAILS[0])},
        vector_hits=[
            RankedHit(mail_id="foreign", score=1),
            RankedHit(mail_id="old", score=0.99),
            RankedHit(mail_id="m3", score=0.9),
            RankedHit(mail_id="m3", score=0.89),
            RankedHit(mail_id="m1", score=0.8),
        ],
    )
    assert [(row.mail_id, row.score) for row in duplicated] == [
        (row.mail_id, row.score) for row in baseline
    ]


def test_answer_port_receives_effective_overrides_instead_of_only_original_question():
    answerer = SyntheticAnswerer()
    target = service(answerer=answerer)
    first = search(target)
    search(target, search_id=first.search_id, overrides={"period": None})
    assert answerer.calls[-1]["parsed"].filters.period is None
    assert "partial" in {row.mail_id for row in answerer.calls[-1]["mails"]}


def test_invalid_or_excessive_vector_response_is_bounded_and_not_fake_success():
    class BrokenVectors:
        ready = True

        async def search(self, **_):
            return [{"mail_id": "m1", "score": float("nan")}]

    with pytest.raises(SearchError) as error:
        search(service(semantic=BrokenVectors()))
    assert error.value.code == "semantic_failed"

    class TooManyVectors:
        ready = True

        async def search(self, **_):
            return [{"mail_id": "m1", "score": 0.8}] * 100

    result = search(service(semantic=TooManyVectors()))
    assert result.truncated and len(result.results) == 3


@pytest.mark.parametrize("slow", [False, True])
def test_answer_model_exception_and_timeout_keep_results_and_redact_details(slow):
    class BrokenAnswerer:
        async def answer(self, **_):
            if slow:
                await asyncio.sleep(0.1)
            raise RuntimeError("synthetic-private-model-error")

    result = search(service(answerer=BrokenAnswerer(), model_timeout=0.01))
    assert len(result.results) == 3 and result.answer is None
    assert result.answer_error.code == "answer_failed"
    assert "synthetic-private" not in result.answer_error.message
