"""실제 실행 조립부 + 분리 pgvector DB. Google·AI는 호출 없는 합성 대역이다."""

import json
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_search_semantic_repository import database as database
from test_search_semantic_repository import search_database as search_database
from test_search_semantic_repository import vectors as vectors

from app.ai import search_semantic
from app.ai.interfaces import ProviderIdentity, ProvidersNotConfigured
from app.ai.selection import AISettingsStore
from app.cli import run_mail_api
from app.google_config import GoogleSettings
from app.schemas.mail_api import LocalSession

QUERY = "2026년 10월 초 고속트레이딩 문의"


class SyntheticGeneration:
    identity = ProviderIdentity(provider="ollama", model="synthetic-only", mode="live")
    external_transfer = False

    async def generate(self, request):
        payload = json.loads(request.user_prompt)
        if "mails" in payload:
            return json.dumps(
                {"sentences": [{"mail_id": "m1", "quote": "초단타 매매 검토"}]},
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "filters": {
                    "period": {"year": 2026, "month": 10, "part": "early"},
                    "directions": ["received"],
                },
                "topic": "고속트레이딩",
                "original_terms": ["고속트레이딩"],
                "expansions": ["HFT", "초단타 매매"],
            },
            ensure_ascii=False,
        )


class SyntheticEmbedding:
    # 운영의 live 필터도 검사하려고 대역의 메타데이터만 live로 맞춘다. 실제 모델 호출은 없다.
    identity = ProviderIdentity(provider="ollama", model="synthetic-3d", mode="live")
    external_transfer = False
    dimensions = 3

    def __init__(self, state):
        self.state, self.calls = state, []
        if state == "mismatch":
            self.identity = self.identity.model_copy(update={"model": "different-model"})

    async def embed(self, request):
        self.calls.append(request)
        if self.state == "failure":
            raise RuntimeError("synthetic-private-error-must-not-escape")
        return [[1, 0, 0]]


@pytest.fixture
def runtime_search(vectors, monkeypatch, tmp_path):
    from test_search_repository import SCOPE

    with vectors.begin() as conn:
        conn.execute(text("UPDATE f1_mail_analysis SET llm_mode='live',embedding_mode='live'"))
        conn.execute(text("UPDATE f1_mail_chunks SET embedding_mode='live'"))
        conn.execute(
            text(
                "UPDATE mails SET subject='HFT 문의',body_text='초단타 매매 검토' "
                "WHERE mail_id='m1'"
            )
        )
    token = "synthetic-search-runtime-only".ljust(43, "-")
    session = LocalSession(**SCOPE.model_dump(), email="synthetic@example.invalid")
    settings = GoogleSettings("synthetic", "synthetic", session.email, Fernet.generate_key())
    monkeypatch.setattr(run_mail_api, "read_api_token", lambda: token)
    monkeypatch.setattr(run_mail_api, "load_settings", lambda: settings)
    monkeypatch.setattr(run_mail_api, "database_engine", lambda: vectors)
    monkeypatch.setattr(
        run_mail_api, "AISettingsStore", lambda: AISettingsStore(tmp_path, values={})
    )
    monkeypatch.setattr(run_mail_api, "SelectedGeneration", lambda _: SyntheticGeneration())
    monkeypatch.setattr(
        run_mail_api, "MailQueryRepository", lambda *_: SimpleNamespace(session=lambda: session)
    )
    monkeypatch.setattr(
        run_mail_api,
        "build_auto_analysis",
        lambda *_, **__: SimpleNamespace(state="not_configured", kick=lambda: None),
    )
    monkeypatch.setattr(run_mail_api, "HistoryRunner", lambda *_, **__: object())
    monkeypatch.setattr(search_semantic, "environment_values", lambda: {"AI_PROVIDER": "claude"})
    monkeypatch.setattr("sys.argv", ["run_mail_api", "--port", "49151"])

    def assemble(state):
        embedding = SyntheticEmbedding(state)

        def local_embedding(values):
            assert values["AI_PROVIDER"] == "ollama"
            if state == "missing":
                raise ProvidersNotConfigured("합성 미설정")
            return embedding

        captured = []
        monkeypatch.setattr(search_semantic, "load_embedding", local_embedding)
        monkeypatch.setattr(run_mail_api.uvicorn, "run", lambda app, **_: captured.append(app))
        run_mail_api.main()
        assert len(captured) == 1
        return captured[0], embedding, token

    return assemble


@pytest.mark.parametrize("state", ["available", "missing", "failure", "mismatch"])
def test_runtime_connects_local_vectors_and_keeps_keywords(runtime_search, vectors, state):
    with vectors.connect() as conn:
        before = conn.execute(
            text("SELECT chunk_id,embedding::text FROM f1_mail_chunks ORDER BY chunk_id")
        ).all()
    application, embedding, token = runtime_search(state)
    assert (application.state.search_service.semantic is None) == (state == "missing")
    with TestClient(
        application, base_url="http://127.0.0.1", client=("127.0.0.1", 10000)
    ) as client:
        headers = {"Authorization": f"Bearer {token}"}
        assert client.post("/search", json={"query": QUERY}).status_code == 401
        response = client.post("/search", json={"query": QUERY}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["parsed"]["original_terms"] == ["고속트레이딩"]
        assert data["parsed"]["filters"]["period"] == {
            "start": "2026-10-01",
            "end_before": "2026-10-11",
        }
        assert data["answer"]["citations"][0]["mail_id"] == "m1"
        assert data["results"][0]["mail_id"] == "m1"
        if state == "available":
            assert data["semantic_enabled"]
            assert data["semantic_coverage"]["compatible_mails"] == 2
            assert {row["mail_id"] for row in data["results"]} == {"m1", "m2"}
            assert set(data["results"][0]["sources"]) == {"keyword", "vector"}
        else:
            assert not data["semantic_enabled"]
            assert [row["mail_id"] for row in data["results"]] == ["m1"]
            assert data["results"][0]["sources"] == ["keyword"]
            code = {
                "missing": "semantic_unavailable",
                "failure": "semantic_failed",
                "mismatch": "embedding_incomplete",
            }[state]
            assert code in {row["code"] for row in data["search_warnings"]}
        assert "synthetic-private-error" not in response.text
        stream = client.post(
            "/search",
            json={"query": QUERY},
            headers={**headers, "Accept": "application/x-ndjson"},
        )
        frames = [json.loads(line) for line in stream.text.splitlines()]
        assert [frame["type"] for frame in frames] == ["parsed", "results", "answer"]
        assert frames[1]["data"]["semantic_coverage"] == data["semantic_coverage"]
        assert frames[1]["data"]["search_warnings"] == data["search_warnings"]
    if state != "missing":
        assert embedding.calls and all(call.purpose == "query" for call in embedding.calls)
    with vectors.connect() as conn:
        assert (
            before
            == conn.execute(
                text("SELECT chunk_id,embedding::text FROM f1_mail_chunks ORDER BY chunk_id")
            ).all()
        )
