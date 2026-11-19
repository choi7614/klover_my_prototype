"""F3 전용 테이블 매핑. 생성/변경은 적용 전 Alembic 패치로만 준비한다."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    MetaData,
    Table,
    Text,
    and_,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.models import MailAccount
from app.schemas.search import ParsedQuery, RecentSearch, SearchOverrides, SearchScope, StoredSearch
from app.services.search_rules import SearchError

search_metadata = MetaData()
search_runs = Table(
    "search_runs",
    search_metadata,
    Column("search_id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("account_id", Text, nullable=False),
    Column("query", Text, nullable=False),
    Column("parsed", JSONB, nullable=False),
    Column("overrides", JSONB, nullable=False),
    Column("reference_date", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["account_id", "user_id"],
        [MailAccount.__table__.c.account_id, MailAccount.__table__.c.user_id],
        name="fk_search_run_account_owner",
    ),
    Index("ix_search_run_owner_created", "user_id", "account_id", "created_at"),
)


def _owner(scope):
    return and_(
        search_runs.c.user_id == scope.user_id,
        search_runs.c.account_id == scope.account_id,
    )


class SQLRecentSearchRepository:
    def __init__(self, engine):
        self.engine = engine

    def save(
        self,
        scope: SearchScope,
        search_id: str,
        query: str,
        parsed: ParsedQuery,
        overrides: SearchOverrides,
        reference_date: date,
    ) -> None:
        with self.engine.begin() as connection:
            account = connection.scalar(
                select(MailAccount.account_id).where(
                    MailAccount.account_id == scope.account_id,
                    MailAccount.user_id == scope.user_id,
                )
            )
            if account is None:
                raise SearchError("scope_unavailable", "연결 계정을 확인해 주세요.", 503)
            connection.execute(
                search_runs.insert().values(
                    search_id=search_id,
                    user_id=scope.user_id,
                    account_id=scope.account_id,
                    query=query,
                    parsed=parsed.model_dump(mode="json"),
                    overrides=overrides.model_dump(mode="json", exclude_unset=True),
                    reference_date=reference_date.isoformat(),
                    created_at=datetime.now(UTC),
                )
            )

    def get(self, scope: SearchScope, search_id: str) -> StoredSearch | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(search_runs).where(
                        _owner(scope),
                        search_runs.c.search_id == search_id,
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            return StoredSearch.model_validate(
                {name: row[name] for name in StoredSearch.model_fields}
            )

    def recent(self, scope: SearchScope) -> list[RecentSearch]:
        ranked = (
            select(
                search_runs,
                func.row_number()
                .over(
                    partition_by=search_runs.c.query,
                    order_by=[search_runs.c.created_at.desc(), search_runs.c.search_id.desc()],
                )
                .label("position"),
            )
            .where(_owner(scope))
            .subquery()
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(ranked)
                .where(ranked.c.position == 1)
                .order_by(
                    ranked.c.created_at.desc(),
                    ranked.c.search_id.desc(),
                )
                .limit(3)
            ).mappings()
            return [
                RecentSearch(**{name: row[name] for name in RecentSearch.model_fields})
                for row in rows
            ]
