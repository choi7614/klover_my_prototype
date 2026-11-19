from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.schemas.search import (
    DateRange,
    ParsedQuery,
    ParseOutput,
    RelativePeriod,
    SearchFilters,
    SearchOverrides,
    SearchRequest,
)
from app.services.search_rules import (
    SearchError,
    apply_overrides,
    korean_date,
    normalize_intent,
    require_supported,
    resolve_period,
)


@pytest.mark.parametrize(
    "relative,today,start,end",
    [
        ("last_month", "2026-01-01", "2025-12-01", "2026-01-01"),
        ("last_month", "2024-03-31", "2024-02-01", "2024-03-01"),
        ("this_week", "2026-11-16", "2026-11-16", "2026-11-23"),
        ("this_week", "2026-11-22", "2026-11-16", "2026-11-23"),
        ("yesterday", "2026-01-01", "2025-12-31", "2026-01-01"),
    ],
)
def test_korean_date_ranges_are_inclusive_start_exclusive_end(relative, today, start, end):
    assert resolve_period(
        RelativePeriod(relative=relative), date.fromisoformat(today)
    ) == DateRange(
        start=start,
        end_before=end,
    )


def test_utc_midnight_boundary_uses_seoul_and_injected_clock():
    assert korean_date(datetime(2026, 11, 18, 14, 59, tzinfo=UTC)) == date(2026, 11, 18)
    assert korean_date(datetime(2026, 11, 18, 15, 0, tzinfo=UTC)) == date(2026, 11, 19)
    with pytest.raises(ValueError):
        korean_date(datetime(2026, 11, 19))
    parsed = normalize_intent(
        ParseOutput(
            filters={"period": {"relative": "yesterday"}},
            topic="예산",
        ),
        date(2026, 11, 19),
    )
    assert parsed.filters.period == DateRange(start="2026-11-18", end_before="2026-11-19")


def test_override_null_removes_conditions_and_never_restores_old_expansions():
    base = ParsedQuery(
        filters={"period": {"start": "2026-10-01", "end_before": "2026-11-01"}},
        topic="예산",
        expansions=["비용 재배정"],
    )
    first, saved = apply_overrides(
        base, SearchOverrides(), SearchOverrides(period=None, topic=None)
    )
    assert first.filters.period is None and first.topic is None and first.expansions == []
    second, _ = apply_overrides(base, saved, SearchOverrides(directions=["sent"]))
    assert second.filters.period is None and second.topic is None and second.expansions == []
    changed, _ = apply_overrides(base, saved, SearchOverrides(topic="문서-123"))
    assert changed.topic == "문서-123" and changed.expansions == []


@pytest.mark.parametrize(
    "value",
    [
        {"needs_reply": False},
        {"replied": False},
        {"has_attachment": False},
        {"category": "notice"},
        {"counterparty": {"kind": "organization", "value": "영업기획팀"}},
    ],
)
def test_unstored_information_is_explicitly_unsupported_even_for_false(value):
    with pytest.raises(SearchError, match="아직 저장하지"):
        require_supported(SearchFilters(**value))


@pytest.mark.parametrize(
    "payload",
    [
        {"query": " "},
        {"query": "예산", "user_id": "other"},
        {"query": "예산", "account_id": "other"},
        {"query": "예산", "parsed": {}},
        {"query": "예산", "overrides": {"directions": ["sent", "sent"]}},
        {
            "query": "예산",
            "overrides": {"period": {"start": "2026-11-02", "end_before": "2026-11-01"}},
        },
        {"query": "예산", "overrides": {"unknown": True}},
    ],
)
def test_request_rejects_invalid_or_owner_controlled_input(payload):
    with pytest.raises(ValidationError):
        SearchRequest.model_validate(payload)


def test_empty_or_unknown_model_interpretation_is_not_success():
    for payload in [
        {},
        {"filters": {}, "topic": None},
        {"filters": {}, "topic": "예산", "user_id": "x"},
    ]:
        with pytest.raises(ValidationError):
            ParseOutput.model_validate(payload)
