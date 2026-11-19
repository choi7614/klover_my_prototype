"""F3 검색 조정. 모델 미연결은 명시적으로 실패하며 가짜 성공을 만들지 않는다."""

import asyncio
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime
from uuid import uuid4

from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.schemas.search import (
    AnswerDraft,
    Citation,
    ParsedQuery,
    ParseOutput,
    RankedHit,
    SearchAnswer,
    SearchFailure,
    SearchMail,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchScope,
)
from app.services.search_ports import QueryParser, SearchAnswerer, SemanticSearch
from app.services.search_rules import (
    SEOUL,
    SearchError,
    apply_overrides,
    condition_matches,
    keyword_terms,
    korean_date,
    normalize_intent,
    require_supported,
)


def _snippet(mail: SearchMail, terms: tuple[str, ...]) -> tuple[str, list[str]]:
    text = mail.body_text or mail.subject
    found = [term for term in terms if term in text.casefold()]
    positions = [text.casefold().find(term) for term in found]
    start = max(0, min(positions, default=0) - 60)
    snippet = text[start : start + 260]
    return snippet, [term for term in found if term in snippet.casefold()]


def combine_results(
    *,
    scope: SearchScope,
    parsed: ParsedQuery,
    mails: tuple[SearchMail, ...],
    keyword_ids: list[str],
    vector_hits: list[RankedHit],
    limit: int,
) -> tuple[list[SearchResult], list[SearchResult], bool]:
    """메일당 한 표씩 RRF로 합친다. 청크 중복은 점수를 부풀리지 않는다."""
    eligible = {
        mail.mail_id: mail
        for mail in mails
        if mail.user_id == scope.user_id
        and mail.account_id == scope.account_id
        and mail.received_at >= scope.sync_started_at
    }
    scores = defaultdict(float)
    sources = defaultdict(list)
    vector_ids = [
        hit.mail_id for hit in sorted(vector_hits, key=lambda hit: (-hit.score, hit.mail_id))
    ]
    for source, identifiers in [
        ("keyword" if parsed.topic else "metadata", keyword_ids),
        ("vector", vector_ids),
    ]:
        identifiers = [identifier for identifier in identifiers if identifier in eligible]
        for rank, identifier in enumerate(dict.fromkeys(identifiers), 1):
            scores[identifier] += 1 / (60 + rank)
            sources[identifier].append(source)
    terms = keyword_terms(parsed)
    full, partial = [], []
    for mail in eligible.values():
        # 저장소 경계 외에 어댑터의 잘못된 반환도 다시 제한한다.
        if (
            mail.mail_id not in scores
            or mail.user_id != scope.user_id
            or mail.account_id != scope.account_id
            or mail.received_at < scope.sync_started_at
        ):
            continue
        matches = condition_matches(mail, parsed.filters)
        missing = [key for key, value in matches.items() if not value]
        if missing and not (any(matches.values()) or terms):
            continue
        snippet, match_terms = _snippet(mail, terms)
        reason = " · ".join(key + " 일치" for key, value in matches.items() if value)
        method = (
            "의미 검색 일치"
            if "vector" in sources[mail.mail_id]
            else ("키워드 일치" if terms else "저장된 메일 조건 일치")
        )
        result = SearchResult(
            mail_id=mail.mail_id,
            number=0,
            score=scores[mail.mail_id],
            reason=" · ".join(filter(None, [reason, method])),
            snippet=snippet,
            match_terms=match_terms,
            missing_conditions=missing,
            sources=sources[mail.mail_id],
            subject=mail.subject,
            from_name=mail.from_name,
            from_addr=mail.from_addr,
            received_at=mail.received_at,
            direction=mail.direction,
        )
        (partial if missing else full).append(result)
    for group in (full, partial):
        group.sort(key=lambda row: (-row.score, -row.received_at.timestamp(), row.mail_id))
    truncated = max(len(full), len(partial)) > limit
    full, partial = full[:limit], partial[:limit]
    full = [row.model_copy(update={"number": index}) for index, row in enumerate(full, 1)]
    partial = [
        row.model_copy(update={"number": index}) for index, row in enumerate(partial, len(full) + 1)
    ]
    return full, partial, truncated


def validate_answer(draft: AnswerDraft, mails: tuple[SearchMail, ...], results) -> SearchAnswer:
    allowed = {mail.mail_id: mail for mail in mails}
    numbers = {result.mail_id: result.number for result in results}
    citations = {}
    text = []
    for sentence in draft.sentences:
        mail = allowed.get(sentence.mail_id)
        if (
            mail is None
            or sentence.mail_id not in numbers
            or not any(sentence.quote in part for part in (mail.subject, mail.body_text))
        ):
            raise SearchError("invalid_answer", "답변의 근거를 확인하지 못했어요.", 502)
        number = numbers[sentence.mail_id]
        citations[number] = Citation(number=number, mail_id=sentence.mail_id)
        text.append(f"{sentence.quote} [{number}]")
    return SearchAnswer(
        text=" ".join(text),
        sentences=draft.sentences,
        citations=list(citations.values()),
    )


class SearchService:
    def __init__(
        self,
        repository,
        recent_repository,
        *,
        parser: QueryParser | None = None,
        answerer: SearchAnswerer | None = None,
        semantic: SemanticSearch | None = None,
        clock: Callable[[], date | datetime] = lambda: datetime.now(SEOUL),
        model_timeout: float = 10,
        result_limit: int = 20,
    ):
        if not 1 <= result_limit <= 100 or not 0 < model_timeout <= 60:
            raise ValueError("결과 수와 모델 대기 시간을 확인하세요")
        self.repository, self.recent_repository = repository, recent_repository
        self.parser, self.answerer, self.semantic = parser, answerer, semantic
        self.clock, self.model_timeout, self.result_limit = clock, model_timeout, result_limit

    async def _parse(self, request: SearchRequest, scope: SearchScope):
        reference_date = korean_date(self.clock())
        previous = request.overrides.__class__()
        if request.search_id:
            record = await run_in_threadpool(self.recent_repository.get, scope, request.search_id)
            if record is None:
                raise SearchError("not_found", "이전 검색을 찾지 못했어요.", 404)
            if record.query != request.query:
                raise SearchError("invalid_search", "새 질문은 새 검색으로 시작해 주세요.")
            base, previous, reference_date = record.parsed, record.overrides, record.reference_date
        else:
            if self.parser is None:
                raise SearchError(
                    "parser_unavailable", "질문 해석 기능이 아직 연결되지 않았어요.", 503
                )
            try:
                output = await asyncio.wait_for(
                    self.parser.parse(query=request.query, reference_date=reference_date),
                    timeout=self.model_timeout,
                )
                output = ParseOutput.model_validate(output)
                base = normalize_intent(output, reference_date)
            except (ValidationError, ValueError, TypeError):
                raise SearchError(
                    "parse_failed", "질문을 이해하지 못했어요. 조건을 확인해 주세요."
                ) from None
            except Exception:
                raise SearchError(
                    "parse_unavailable", "질문을 해석하지 못했어요. 다시 시도해 주세요.", 503
                ) from None
        parsed, overrides = apply_overrides(base, previous, request.overrides)
        require_supported(parsed.filters)
        search_id = uuid4().hex
        await run_in_threadpool(
            self.recent_repository.save,
            scope,
            search_id,
            request.query,
            base,
            overrides,
            reference_date,
        )
        return parsed, search_id, reference_date

    async def events(self, request: SearchRequest, scope: SearchScope):
        parsed, search_id, reference_date = await self._parse(request, scope)
        yield {
            "type": "parsed",
            "data": {
                "parsed": parsed.model_dump(mode="json"),
                "search_id": search_id,
                "reference_date": reference_date.isoformat(),
            },
        }
        candidates = await run_in_threadpool(self.repository.candidates, scope, parsed)
        identifiers = [mail.mail_id for mail in (*candidates.full, *candidates.partial)]
        vector_hits = []
        vector_truncated = False
        semantic_enabled = bool(self.semantic and self.semantic.ready and parsed.topic)
        if semantic_enabled:
            try:
                hits = await asyncio.wait_for(
                    self.semantic.search(scope=scope, parsed=parsed, limit=self.result_limit * 2),
                    self.model_timeout,
                )
                vector_truncated = len(hits) > self.result_limit * 2
                vector_hits = [
                    RankedHit.model_validate(hit) for hit in hits[: self.result_limit * 2]
                ]
            except Exception:
                raise SearchError(
                    "semantic_failed", "의미 검색을 완료하지 못했어요.", 503
                ) from None
        identifiers.extend(hit.mail_id for hit in vector_hits)
        mails = await run_in_threadpool(
            self.repository.hydrate, scope, list(dict.fromkeys(identifiers))
        )
        results, partial, truncated = combine_results(
            scope=scope,
            parsed=parsed,
            mails=mails,
            keyword_ids=identifiers[: len(candidates.full) + len(candidates.partial)],
            vector_hits=vector_hits,
            limit=self.result_limit,
        )
        yield {
            "type": "results",
            "data": {
                "results": [result.model_dump(mode="json") for result in results],
                "partial": [result.model_dump(mode="json") for result in partial],
                "semantic_enabled": semantic_enabled,
                "truncated": candidates.truncated or truncated or vector_truncated,
            },
        }
        if not results:
            answer = SearchAnswer(text="찾은 메일이 없습니다", sentences=[], citations=[])
        elif self.answerer is None:
            yield {
                "type": "answer_error",
                "data": {
                    "code": "answer_unavailable",
                    "message": "답변 기능이 아직 연결되지 않았어요. 검색 결과를 확인해 주세요.",
                },
            }
            return
        else:
            evidence = tuple(
                mail for mail in mails if mail.mail_id in {row.mail_id for row in results}
            )
            try:
                output = await asyncio.wait_for(
                    self.answerer.answer(query=request.query, parsed=parsed, mails=evidence),
                    self.model_timeout,
                )
            except Exception:
                yield {
                    "type": "answer_error",
                    "data": {
                        "code": "answer_failed",
                        "message": "답변을 만들지 못했어요. 검색 결과를 확인해 주세요.",
                    },
                }
                return
            try:
                draft = AnswerDraft.model_validate(output)
                answer = validate_answer(draft, evidence, results)
            except Exception:
                yield {
                    "type": "answer_error",
                    "data": {
                        "code": "invalid_answer",
                        "message": "답변의 근거를 확인하지 못했어요. 검색 결과를 확인해 주세요.",
                    },
                }
                return
        yield {"type": "answer", "data": answer.model_dump(mode="json")}

    async def search(self, request: SearchRequest, scope: SearchScope) -> SearchResponse:
        data = {}
        async for event in self.events(request, scope):
            if event["type"] in {"parsed", "results"}:
                data.update(event["data"])
            elif event["type"] == "answer":
                data["answer"] = event["data"]
            else:
                data["answer_error"] = SearchFailure.model_validate(event["data"])
        return SearchResponse.model_validate(data)
