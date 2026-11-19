"""실제 AI 없이 F3 해석기·답변기가 공통 생성 계약과 검색 계약을 지키는지 확인한다."""

import asyncio
import json

import pytest
from search_support import MAILS, SCOPE, TODAY, SyntheticHistory, SyntheticRepository

from app.ai.interfaces import ProviderCallError, ProviderIdentity, ProvidersNotConfigured
from app.ai.search_adapter import SharedQueryParser, SharedSearchAnswerer
from app.schemas.search import ParsedQuery, SearchRequest
from app.services.search import SearchService
from app.services.search_ports import ModelOutputInvalid
from app.services.search_rules import SearchError

PARSE_OK = json.dumps(
    {"filters": {"period": {"relative": "last_month"}}, "topic": "예산", "expansions": ["비용"]},
    ensure_ascii=False,
)


class ScriptedGeneration:
    """요청을 기록하고 정해진 응답을 차례로 돌려주는 합성 제공자."""

    identity = ProviderIdentity(provider="f3-test-double", model="synthetic-json", mode="test")

    def __init__(self, *responses, delay=0.0):
        self.responses, self.requests, self.delay = list(responses), [], delay

    async def generate(self, request):
        self.requests.append(request)
        if self.delay:
            await asyncio.sleep(self.delay)
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(request)
        return response


def answer_from_mails(request):
    mails = json.loads(request.user_prompt)["mails"]
    return json.dumps(
        {"sentences": [{"mail_id": m["mail_id"], "quote": m["body_text"]} for m in mails]},
        ensure_ascii=False,
    )


def parse(generator):
    return asyncio.run(
        SharedQueryParser(generator, allow_test_provider=True).parse(
            query="지난달 예산 메일", reference_date=TODAY
        )
    )


def service(parse_gen, answer_gen=None, **kwargs):
    return SearchService(
        SyntheticRepository(),
        SyntheticHistory(),
        parser=SharedQueryParser(parse_gen, allow_test_provider=True),
        answerer=SharedSearchAnswerer(answer_gen or parse_gen, allow_test_provider=True),
        clock=lambda: TODAY,
        **kwargs,
    )


def run_search(target):
    return asyncio.run(target.search(SearchRequest(query="지난달 예산 메일"), SCOPE))


def test_parser_uses_common_contract_and_sends_only_query_and_date():
    generator = ScriptedGeneration(PARSE_OK)
    output = parse(generator)
    assert output.topic == "예산"
    request = generator.requests[0]
    assert request.purpose == "search"
    assert request.response_schema["title"] == "ParseOutput"
    assert "신뢰할 수 없는 데이터" in request.system_prompt
    assert json.loads(request.user_prompt) == {
        "query": "지난달 예산 메일",
        "reference_date": TODAY.isoformat(),
    }


@pytest.mark.parametrize(
    "wrapped", [f"```json\n{PARSE_OK}\n```", f"```\n{PARSE_OK}```", f"  {PARSE_OK}\n"]
)
def test_parser_accepts_code_fence_from_local_models(wrapped):
    generator = ScriptedGeneration(wrapped)
    assert parse(generator).topic == "예산"
    assert len(generator.requests) == 1


def test_parser_retries_once_without_echoing_bad_output():
    generator = ScriptedGeneration("설명: private-bad-output", PARSE_OK)
    assert parse(generator).topic == "예산"
    assert len(generator.requests) == 2
    retry = json.loads(generator.requests[1].user_prompt)
    assert "previous_attempt_error" in retry
    assert "private-bad-output" not in generator.requests[1].user_prompt


@pytest.mark.parametrize(
    "bad",
    ["not json", '{"filters": {}, "topic": null}', '{"filters": {}, "topic": "x", "extra": 1}'],
)
def test_parser_gives_up_after_two_attempts(bad):
    generator = ScriptedGeneration(bad)
    with pytest.raises(ModelOutputInvalid):
        parse(generator)
    assert len(generator.requests) == 2


def test_provider_error_is_not_retried():
    generator = ScriptedGeneration(ProviderCallError("synthetic"))
    with pytest.raises(ProviderCallError):
        parse(generator)
    assert len(generator.requests) == 1


def test_test_provider_is_rejected_without_opt_in():
    for adapter in (SharedQueryParser, SharedSearchAnswerer):
        with pytest.raises(ProvidersNotConfigured):
            adapter(ScriptedGeneration(PARSE_OK))


def test_service_end_to_end_with_shared_adapters():
    answer_gen = ScriptedGeneration(answer_from_mails)
    result = run_search(service(ScriptedGeneration(PARSE_OK), answer_gen))
    assert {row.mail_id for row in result.results} == {"m1", "m2", "m3"}
    assert result.answer and len(result.answer.citations) == 3
    payload = json.loads(answer_gen.requests[0].user_prompt)
    assert {m["mail_id"] for m in payload["mails"]} == {"m1", "m2", "m3"}
    # 다른 사용자·계정 식별 정보는 외부 호출 입력에 넣지 않는다.
    assert all("user_id" not in m and "account_id" not in m for m in payload["mails"])


@pytest.mark.parametrize(
    "parse_gen,code,status",
    [
        (ScriptedGeneration("깨진 응답"), "parse_failed", 422),
        (ScriptedGeneration(ProviderCallError("synthetic")), "parse_unavailable", 503),
        (ScriptedGeneration(ProvidersNotConfigured("synthetic")), "parser_unavailable", 503),
        (ScriptedGeneration(PARSE_OK, delay=0.5), "parse_unavailable", 503),
    ],
)
def test_service_maps_parser_failures_to_existing_codes(parse_gen, code, status):
    with pytest.raises(SearchError) as error:
        run_search(service(parse_gen, ScriptedGeneration(answer_from_mails), model_timeout=0.1))
    assert (error.value.code, error.value.status) == (code, status)


def test_answer_with_invented_quote_is_retried_then_invalid_answer():
    bad = json.dumps({"sentences": [{"mail_id": "m1", "quote": "메일에 없는 문장"}]})
    answer_gen = ScriptedGeneration(bad)
    result = run_search(service(ScriptedGeneration(PARSE_OK), answer_gen))
    assert result.answer is None
    assert result.answer_error.code == "invalid_answer"
    assert len(answer_gen.requests) == 2
    assert result.results  # 검색 결과 목록은 그대로 보여 준다.


def test_answer_retry_recovers_from_foreign_mail_id():
    bad = json.dumps({"sentences": [{"mail_id": "foreign", "quote": "예산"}]})
    answer_gen = ScriptedGeneration(bad, answer_from_mails)
    result = run_search(service(ScriptedGeneration(PARSE_OK), answer_gen))
    assert result.answer and result.answer_error is None


@pytest.mark.parametrize(
    "failure,code",
    [
        (ProvidersNotConfigured("synthetic"), "answer_unavailable"),
        (ProviderCallError("synthetic"), "answer_failed"),
    ],
)
def test_answer_provider_failures_use_existing_codes(failure, code):
    result = run_search(service(ScriptedGeneration(PARSE_OK), ScriptedGeneration(failure)))
    assert result.answer_error.code == code


def test_answerer_never_receives_mails_outside_results():
    answer_gen = ScriptedGeneration(answer_from_mails)
    asyncio.run(
        SharedSearchAnswerer(answer_gen, allow_test_provider=True).answer(
            query="예산", parsed=ParsedQuery(topic="예산"), mails=MAILS[:1]
        )
    )
    assert [m["mail_id"] for m in json.loads(answer_gen.requests[0].user_prompt)["mails"]] == ["m1"]
