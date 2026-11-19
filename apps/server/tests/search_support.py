"""F3 검사에만 쓰는 합성 메일/모델/저장소. 운영 모듈에서 가져오지 않는다."""

from datetime import UTC, date, datetime

from app.db.repositories.search import SearchCandidates
from app.schemas.search import (
    AnswerDraft,
    ParsedQuery,
    ParseOutput,
    RecentSearch,
    SearchMail,
    SearchScope,
    StoredSearch,
)
from app.services.search_rules import condition_matches, keyword_terms

SCOPE = SearchScope(
    user_id="f3-user",
    account_id="f3-account",
    sync_started_at=datetime(2026, 10, 1, tzinfo=UTC),
)


def mail(identifier="m1", **changes):
    values = dict(
        mail_id=identifier,
        user_id=SCOPE.user_id,
        account_id=SCOPE.account_id,
        received_at=datetime(2026, 10, 24, tzinfo=UTC),
        direction="received",
        from_addr="budget@example.invalid",
        from_name="박지훈",
        to=[{"addr": "self@example.invalid", "name": "합성 수신자"}],
        subject="예산 재배정 요청",
        body_text="다음 분기 예산 재배정을 협의해 주세요.",
    )
    values.update(changes)
    return SearchMail(**values)


MAILS = (
    mail(),
    mail("m2", subject="출장비 예산 초과 문의", body_text="출장비 예산 초과분을 확인해 주세요."),
    mail("m3", subject="예산 전용 문의", body_text="남은 예산을 행사비로 전용할 수 있나요?"),
    mail("partial", received_at=datetime(2026, 11, 10, tzinfo=UTC)),
    mail("foreign", user_id="other-user", account_id="other-account"),
    mail("old", received_at=datetime(2026, 9, 30, tzinfo=UTC)),
)


class SyntheticParser:
    def __init__(self, output=None):
        self.output = (
            output
            if output is not None
            else ParseOutput(
                filters={"period": {"relative": "last_month"}},
                topic="예산",
            )
        )
        self.calls = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.output


class SyntheticAnswerer:
    def __init__(self, output=None):
        self.output, self.calls = output, []

    async def answer(self, **kwargs):
        self.calls.append(kwargs)
        return (
            self.output
            if self.output is not None
            else AnswerDraft(
                sentences=[
                    {"mail_id": row.mail_id, "quote": row.body_text} for row in kwargs["mails"]
                ]
            )
        )


class SyntheticRepository:
    def __init__(self, rows=MAILS):
        self.rows = rows

    def hydrate(self, scope, identifiers):
        return tuple(
            row
            for row in self.rows
            if (
                row.mail_id in identifiers
                and row.user_id == scope.user_id
                and row.account_id == scope.account_id
                and row.received_at >= scope.sync_started_at
            )
        )

    def candidates(self, scope, parsed: ParsedQuery):
        rows = self.hydrate(scope, [row.mail_id for row in self.rows])
        terms = keyword_terms(parsed)
        rows = [
            row
            for row in rows
            if not terms or any(term in (row.subject + row.body_text).casefold() for term in terms)
        ]
        full, partial = [], []
        for row in rows:
            flags = condition_matches(row, parsed.filters)
            if all(flags.values()):
                full.append(row)
            elif any(flags.values()) or terms:
                partial.append(row)
        return SearchCandidates(tuple(full), tuple(partial), False)


class SyntheticHistory:
    def __init__(self):
        self.records = {}

    def save(self, scope, search_id, query, parsed, overrides, reference_date):
        self.records[(scope.user_id, scope.account_id, search_id)] = StoredSearch(
            search_id=search_id,
            query=query,
            parsed=parsed,
            overrides=overrides,
            reference_date=reference_date,
        )

    def get(self, scope, search_id):
        return self.records.get((scope.user_id, scope.account_id, search_id))

    def recent(self, scope):
        return [
            RecentSearch(
                search_id=identifier,
                query=record.query,
                created_at=datetime(2026, 11, 19, tzinfo=UTC),
            )
            for (user, account, identifier), record in self.records.items()
            if (user, account) == (scope.user_id, scope.account_id)
        ][-3:]


TODAY = date(2026, 11, 19)
