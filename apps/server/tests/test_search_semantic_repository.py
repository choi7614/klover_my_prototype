"""실제 PostgreSQL+pgvector, 합성 3차원 벡터만 쓰는 검색 검사."""

import asyncio

import pytest
from sqlalchemy import text
from test_search_memory import Embedding
from test_search_repository import (
    SCOPE,
)
from test_search_repository import (
    database as database,
)
from test_search_repository import (
    search_database as search_database,
)

from app.ai.interfaces import ProviderIdentity
from app.ai.search_semantic import LocalSemanticSearch
from app.db.repositories.search import SQLSearchRepository
from app.db.repositories.search_semantic import SQLSemanticRepository
from app.schemas.search import ParsedQuery


@pytest.fixture
def vectors(search_database):
    with search_database.begin() as conn:
        for mail_id, model, vector, seq in [
            ("m1", "synthetic-3d", [1, 0, 0], 0),
            ("m1", "synthetic-3d", [1, 0, 0], 1),
            ("m2", "synthetic-3d", [0.95, 0.05, 0], 0),
            ("m3", "other-model", [1, 0, 0], 0),
            ("sent", "synthetic-3d", [0, 1, 0], 0),
            ("other-account", "synthetic-3d", [1, 0, 0], 0),
            ("other-user", "synthetic-3d", [1, 0, 0], 0),
            ("pre-start", "synthetic-3d", [1, 0, 0], 0),
            ("spam", "synthetic-3d", [1, 0, 0], 0),
            ("trash", "synthetic-3d", [1, 0, 0], 0),
            ("literal", "synthetic-3d", [1, 0], 0),
        ]:
            conn.execute(
                text("""
                INSERT INTO f1_mail_analysis
                    (mail_id,user_id,account_id,llm_mode,embedding_mode,embedding_provider,
                     embedding_model,embedding_dimensions)
                SELECT mail_id,user_id,account_id,'test','test','ollama',:model,:dim
                FROM mails WHERE mail_id=:id
                ON CONFLICT DO NOTHING
            """),
                {"id": mail_id, "model": model, "dim": len(vector)},
            )
            conn.execute(
                text("""
                INSERT INTO f1_mail_chunks
                    (chunk_id,mail_id,user_id,account_id,kind,seq,text,embedding,
                    embedding_dimensions,embedding_provider,embedding_model,embedding_mode,received_at,category)
                SELECT :chunk,mail_id,user_id,account_id,'body',:seq,
                    '합성 청크',CAST(:vector AS public.vector),
                    :dim,'ollama',:model,'test',received_at,'external' FROM mails WHERE mail_id=:id
            """),
                {
                    "chunk": f"{mail_id}-{seq}",
                    "seq": seq,
                    "vector": str(vector),
                    "dim": len(vector),
                    "model": model,
                    "id": mail_id,
                },
            )
    with search_database.begin() as conn:
        conn.execute(text("UPDATE mails SET analysis_status='done'"))
    return search_database


def run(engine, parsed=None, candidate_limit=2000):
    provider = Embedding([1, 0, 0])
    result = asyncio.run(
        LocalSemanticSearch(
            SQLSemanticRepository(engine, candidate_limit=candidate_limit),
            provider,
            allow_test_provider=True,
        ).search(scope=SCOPE, parsed=parsed or ParsedQuery(topic="다른 표현의 주제"), limit=20)
    )
    assert provider.calls[0].purpose == "query"
    return result


def test_actual_pgvector_distance_dedup_model_dimension_and_scope(vectors):
    result = run(vectors)
    assert [row.mail_id for row in result.hits] == ["m1", "m2"]
    assert result.coverage.eligible_mails == 5  # m1/2/3, sent, literal
    assert result.coverage.compatible_mails == 3
    assert result.coverage.scanned_chunks == 4 and not result.coverage.limited
    assert result.hits[0].score == 1
    with vectors.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_chunks")) == 11


def test_same_period_direction_sender_filters_applied_to_vectors(vectors):
    result = run(
        vectors,
        ParsedQuery(
            topic="주제",
            filters={
                "period": {"start": "2026-10-01", "end_before": "2026-10-02"},
                "directions": ["received"],
                "counterparty": {"kind": "name", "value": "박지훈"},
            },
        ),
    )
    assert [row.mail_id for row in result.hits] == ["m1"]
    assert result.coverage.eligible_mails == 2  # m1 + 다른 차원인 literal


def test_candidate_limit_is_disclosed_and_live_does_not_read_test_vectors(vectors):
    assert run(vectors, candidate_limit=1).coverage.limited
    result = SQLSemanticRepository(vectors).search(
        scope=SCOPE,
        parsed=ParsedQuery(topic="주제"),
        identity=ProviderIdentity(provider="ollama", model="synthetic-3d", mode="live"),
        dimensions=3,
        vector=(1, 0, 0),
        limit=20,
    )
    assert result.hits == () and result.coverage.compatible_mails == 0


def test_keywords_exact_number_and_expansions_share_owner_and_explicit_dates(vectors):
    with vectors.begin() as conn:
        conn.execute(
            text("UPDATE mails SET subject='HFT 문의',body_text='AB-1042' WHERE mail_id='m1'")
        )
        conn.execute(
            text(
                "UPDATE mails SET subject='High-Frequency Trading',body_text='AB-10420' "
                "WHERE mail_id='m2'"
            )
        )
    parsed = ParsedQuery(
        topic="고속트레이딩",
        expansions=["HFT", "High-Frequency Trading"],
        original_terms=["AB-1042"],
    )
    lexical = SQLSearchRepository(vectors).candidates(SCOPE, parsed)
    assert [row.mail_id for row in lexical.full] == ["m1"]
    assert [row.mail_id for row in run(vectors, parsed).hits] == ["m1"]


def test_explicit_history_import_is_searchable_but_not_other_old_mails(vectors):
    with vectors.begin() as conn:
        conn.execute(text("UPDATE mails SET history_imported=true WHERE mail_id='pre-start'"))
    result = run(vectors)
    assert "pre-start" in {row.mail_id for row in result.hits}


def test_http_contract_combines_real_sql_vectors_with_fake_generation(vectors):
    from datetime import date
    from types import SimpleNamespace

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from search_support import SyntheticAnswerer, SyntheticParser

    from app.api.errors import register_error_handlers
    from app.api.mail_read import MailAPIContext
    from app.api.search import register_search_api
    from app.db.repositories.search_recent import SQLRecentSearchRepository
    from app.schemas.mail_api import LocalSession
    from app.schemas.search import ParseOutput
    from app.services.search import SearchService

    with vectors.begin() as conn:
        conn.execute(
            text(
                "UPDATE mails SET subject='HFT 문의',body_text='초단타 매매 검토' "
                "WHERE mail_id='m1'"
            )
        )
        before = conn.execute(
            text("SELECT chunk_id,embedding::text FROM f1_mail_chunks ORDER BY chunk_id")
        ).all()
        indexes = (
            conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes WHERE schemaname=current_schema() "
                    "AND tablename='f1_mail_chunks'"
                )
            )
            .scalars()
            .all()
        )
        assert any("user_id, account_id, received_at" in definition for definition in indexes)
        assert not any("hnsw" in definition or "ivfflat" in definition for definition in indexes)
    application = FastAPI()
    register_error_handlers(application)
    register_search_api(application)
    token = "synthetic-search-only"
    application.state.mail_api = MailAPIContext(
        token,
        SimpleNamespace(
            session=lambda: LocalSession(**SCOPE.model_dump(), email="synthetic@example.invalid")
        ),
    )
    application.state.search_service = SearchService(
        SQLSearchRepository(vectors),
        SQLRecentSearchRepository(vectors),
        parser=SyntheticParser(
            ParseOutput(
                filters={"period": {"month": 10, "part": "early"}, "directions": ["received"]},
                topic="고속트레이딩",
                expansions=["HFT", "초단타 매매"],
                original_terms=["고속트레이딩"],
            )
        ),
        answerer=SyntheticAnswerer(),
        semantic=LocalSemanticSearch(
            SQLSemanticRepository(vectors), Embedding([1, 0, 0]), allow_test_provider=True
        ),
        clock=lambda: date(2026, 11, 25),
    )
    with TestClient(
        application, base_url="http://127.0.0.1", client=("127.0.0.1", 10000)
    ) as client:
        response = client.post(
            "/search",
            json={"query": "누가 보낸진 모르겠고 10월 초 고속트레이딩 문의"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["parsed"]["filters"]["period"] == {
            "start": "2026-10-01",
            "end_before": "2026-10-11",
        }
        assert data["semantic_enabled"] and data["semantic_coverage"]["compatible_mails"] == 2
        assert [row["mail_id"] for row in data["results"]] == ["m1", "m2"]
        assert set(data["results"][0]["sources"]) == {"keyword", "vector"}
        assert all(citation["mail_id"] in {"m1", "m2"} for citation in data["answer"]["citations"])
        assert "embedding_incomplete" in {warning["code"] for warning in data["search_warnings"]}
    with vectors.connect() as conn:
        assert (
            before
            == conn.execute(
                text("SELECT chunk_id,embedding::text FROM f1_mail_chunks ORDER BY chunk_id")
            ).all()
        )


def test_pending_analysis_or_metadata_mismatch_is_not_compatible(vectors):
    with vectors.begin() as conn:
        conn.execute(text("UPDATE mails SET analysis_status='pending' WHERE mail_id='m1'"))
        conn.execute(
            text("UPDATE f1_mail_analysis SET embedding_model='changed' WHERE mail_id='m2'")
        )
    result = run(vectors)
    assert result.hits == ()
    assert result.coverage.compatible_mails == 1  # 주제와 무관한 sent 벡터만 호환된다.
