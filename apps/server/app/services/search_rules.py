"""F3의 순수 검증 규칙. AI나 DB를 호출하지 않는다."""

import calendar
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.schemas.search import (
    DateRange,
    MonthPart,
    ParsedQuery,
    ParseOutput,
    RelativePeriod,
    SearchFilters,
    SearchMail,
    SearchOverrides,
)

SEOUL = ZoneInfo("Asia/Seoul")


class SearchError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def korean_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("기준 시각에는 시간대가 필요합니다")
        return value.astimezone(SEOUL).date()
    return value


def resolve_period(period: RelativePeriod, today: date) -> DateRange:
    if period.relative == "last_month":
        end = today.replace(day=1)
        start = (end - timedelta(days=1)).replace(day=1)
    elif period.relative == "this_week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
    else:
        start, end = today - timedelta(days=1), today
    return DateRange(start=start, end_before=end)


def normalize_intent(output: ParseOutput, today: date) -> ParsedQuery:
    values = output.filters.model_dump()
    if isinstance(output.filters.period, RelativePeriod):
        values["period"] = resolve_period(output.filters.period, today).model_dump()
    elif isinstance(output.filters.period, MonthPart):
        period = output.filters.period
        # 연도가 없으면 기준일보다 미래가 아닌 가장 최근의 해당 월을 쓴다.
        year = period.year or (today.year - (period.month > today.month))
        first, last = {"early": (1, 10), "middle": (11, 20), "late": (21, 31)}[period.part]
        last = min(last, calendar.monthrange(year, period.month)[1])
        values["period"] = DateRange(
            start=date(year, period.month, first),
            end_before=date(year, period.month, last) + timedelta(days=1),
        ).model_dump()
    return ParsedQuery(
        filters=SearchFilters.model_validate(values),
        topic=output.topic,
        expansions=output.expansions,
        original_terms=output.original_terms,
    )


def apply_overrides(
    base: ParsedQuery, previous: SearchOverrides, changes: SearchOverrides
) -> tuple[ParsedQuery, SearchOverrides]:
    merged = {**previous.model_dump(exclude_unset=True), **changes.model_dump(exclude_unset=True)}
    filters = base.filters.model_dump()
    filters.update({key: value for key, value in merged.items() if key != "topic"})
    topic = merged.get("topic", base.topic)
    # 지운/고친 주제의 확장어가 뒤 검색에 남으면 안 된다.
    expansions = [] if "topic" in merged else base.expansions
    parsed = ParsedQuery(
        filters=SearchFilters(**filters),
        topic=topic,
        expansions=expansions,
        original_terms=[] if "topic" in merged else base.original_terms,
    )
    return parsed, SearchOverrides.model_validate(merged)


def require_supported(filters: SearchFilters) -> None:
    missing = [
        key
        for key in ("needs_reply", "replied", "category", "has_attachment")
        if getattr(filters, key) is not None
    ]
    if filters.counterparty and filters.counterparty.kind == "organization":
        missing.append("organization")
    if missing:
        raise SearchError(
            "unsupported_filter",
            "아직 저장하지 않는 조건입니다: " + ", ".join(missing),
        )


def keyword_terms(parsed: ParsedQuery) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            t.casefold() for t in [parsed.topic, *parsed.original_terms, *parsed.expansions] if t
        )
    )


def midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=SEOUL)


def condition_matches(mail: SearchMail, filters: SearchFilters) -> dict[str, bool]:
    matches = {}
    if filters.period:
        matches["기간"] = (
            midnight(filters.period.start) <= mail.received_at < midnight(filters.period.end_before)
        )
    if filters.directions:
        matches["대상"] = mail.direction in filters.directions
    if filters.counterparty:
        party = filters.counterparty
        values = (
            [mail.from_addr if party.kind == "address" else mail.from_name]
            if mail.direction == "received"
            else [
                person.get("addr" if party.kind == "address" else "name", "") for person in mail.to
            ]
        )
        matches["상대"] = any(
            value.casefold() == party.value.casefold()
            if party.kind == "address"
            else party.value.casefold() in value.casefold()
            for value in values
        )
    return matches


_EXACT = re.compile(
    r"(?<!\w)(?:[A-Za-z가-힣]+[-#]\d[\w-]*|\d[\d,]*(?:\.\d+)?(?:만?원|달러)?)(?!\w)"
)


def exact_terms(parsed: ParsedQuery) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            match.group(0).casefold()
            for term in [parsed.topic, *parsed.original_terms]
            if term
            for match in _EXACT.finditer(term)
        )
    )


def exact_terms_match(mail: SearchMail, parsed: ParsedQuery) -> bool:
    # 벡터의 주제 유사성으로 다른 문서 번호·금액을 정답에 섞지 않는다.
    return all(
        any(
            re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", part.casefold())
            for part in (mail.subject, mail.body_text)
        )
        for term in exact_terms(parsed)
    )
