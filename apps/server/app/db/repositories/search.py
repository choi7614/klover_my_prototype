"""F3 전용 읽기 저장소. 최소 저장 모델의 실제 열만 검색한다."""

import re
from dataclasses import dataclass

from sqlalchemy import and_, case, func, not_, or_, select
from sqlalchemy.orm import Session

from app.db.models import Mail, MailAccount
from app.schemas.search import ParsedQuery, SearchMail, SearchScope
from app.services.search_rules import exact_terms, keyword_terms, midnight, require_supported


@dataclass(frozen=True)
class SearchCandidates:
    full: tuple[SearchMail, ...]
    partial: tuple[SearchMail, ...]
    truncated: bool


def _literal_pattern(value):
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _like(column, value):
    return column.ilike(_literal_pattern(value), escape="\\")


def _exact_conditions(parsed):
    return [
        or_(
            Mail.subject.op("~*")(r"(?<![[:alnum:]_])" + re.escape(term) + r"(?![[:alnum:]_])"),
            Mail.body_text.op("~*")(r"(?<![[:alnum:]_])" + re.escape(term) + r"(?![[:alnum:]_])"),
        )
        for term in exact_terms(parsed)
    ]


def _conditions(filters):
    require_supported(filters)
    clauses = []
    if filters.period:
        clauses.append(
            and_(
                Mail.received_at >= midnight(filters.period.start),
                Mail.received_at < midnight(filters.period.end_before),
            )
        )
    if filters.directions:
        clauses.append(Mail.direction.in_(filters.directions))
    if filters.counterparty:
        party = filters.counterparty
        field = "addr" if party.kind == "address" else "name"
        recipients = func.jsonb_array_elements(Mail.to).table_valued("value")

        def matches(column):
            return (
                func.lower(column) == party.value.lower()
                if party.kind == "address"
                else _like(column, party.value)
            )

        sender = matches(Mail.from_addr if field == "addr" else Mail.from_name)
        recipient = (
            select(1)
            .select_from(recipients)
            .where(matches(recipients.c.value.op("->>")(field)))
            .exists()
        )
        clauses.append(
            or_(
                and_(Mail.direction == "received", sender),
                and_(Mail.direction == "sent", recipient),
            )
        )
    return clauses


def _scope_query(scope):
    # 계정 행과도 비교하므로 오래된 scope로 시작 시점을 넓힐 수 없다.
    return (
        select(Mail)
        .join(
            MailAccount,
            and_(
                MailAccount.account_id == Mail.account_id,
                MailAccount.user_id == Mail.user_id,
            ),
        )
        .where(
            Mail.user_id == scope.user_id,
            Mail.account_id == scope.account_id,
            MailAccount.user_id == scope.user_id,
            or_(Mail.received_at >= scope.sync_started_at, Mail.history_imported.is_(True)),
            or_(Mail.received_at >= MailAccount.sync_started_at, Mail.history_imported.is_(True)),
            Mail.mailbox.in_(["inbox", "sent", "archive"]),
        )
    )


def _mail(row):
    return SearchMail.model_validate({name: getattr(row, name) for name in SearchMail.model_fields})


class SQLSearchRepository:
    def __init__(self, engine, candidate_limit: int = 100):
        if not 1 <= candidate_limit <= 500:
            raise ValueError("후보 수는 1~500이어야 합니다")
        self.engine, self.candidate_limit = engine, candidate_limit

    def candidates(self, scope: SearchScope, parsed: ParsedQuery) -> SearchCandidates:
        conditions = _conditions(parsed.filters)
        terms = keyword_terms(parsed)
        term_matches = [
            or_(_like(Mail.subject, term), _like(Mail.body_text, term)) for term in terms
        ]
        score = sum(
            (
                case((_like(Mail.subject, term), 2), else_=0)
                + case((_like(Mail.body_text, term), 1), else_=0)
            )
            for term in terms
        )
        query = _scope_query(scope).where(*_exact_conditions(parsed))
        if parsed.filters.period:
            query = query.where(
                Mail.received_at >= midnight(parsed.filters.period.start),
                Mail.received_at < midnight(parsed.filters.period.end_before),
            )
        if terms:
            query = query.where(or_(*term_matches))
        if terms:
            query = query.order_by(score.desc())
        query = query.order_by(Mail.received_at.desc(), Mail.mail_id.asc())
        full_query = query.where(and_(*conditions)) if conditions else query
        partial_query = None
        if conditions:
            # 주제와 일치하거나 다른 구조화 조건을 만족하는 후보만 일부 일치로 표시한다.
            partial_query = query.where(not_(and_(*conditions)))
            if not terms:
                partial_query = partial_query.where(or_(*conditions))
        with Session(self.engine) as session:
            full = list(session.scalars(full_query.limit(self.candidate_limit + 1)))
            partial = (
                list(session.scalars(partial_query.limit(self.candidate_limit + 1)))
                if partial_query is not None
                else []
            )
            return SearchCandidates(
                full=tuple(_mail(row) for row in full[: self.candidate_limit]),
                partial=tuple(_mail(row) for row in partial[: self.candidate_limit]),
                truncated=max(len(full), len(partial)) > self.candidate_limit,
            )

    def hydrate(self, scope: SearchScope, identifiers: list[str]) -> tuple[SearchMail, ...]:
        if not identifiers:
            return ()
        with Session(self.engine) as session:
            return tuple(
                _mail(row)
                for row in session.scalars(_scope_query(scope).where(Mail.mail_id.in_(identifiers)))
            )
