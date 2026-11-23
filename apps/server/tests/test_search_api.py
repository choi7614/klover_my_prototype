import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from search_support import (
    SCOPE,
    TODAY,
    SyntheticAnswerer,
    SyntheticHistory,
    SyntheticParser,
    SyntheticRepository,
)

from app.api.errors import register_error_handlers
from app.api.mail_read import MailAPIContext
from app.api.search import register_search_api
from app.main import create_app
from app.schemas.mail_api import LocalSession
from app.services.search import SearchService

TOKEN = "f3-synthetic-test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class Identity:
    def session(self):
        return LocalSession(
            **SCOPE.model_dump(),
            email="synthetic@example.invalid",
        )


def client_for(*, parser=True, **kwargs):
    application = FastAPI()
    register_error_handlers(application)
    register_search_api(application)
    application.state.mail_api = MailAPIContext(TOKEN, Identity())
    application.state.search_service = SearchService(
        SyntheticRepository(),
        SyntheticHistory(),
        parser=SyntheticParser() if parser else None,
        answerer=SyntheticAnswerer(),
        clock=lambda: TODAY,
    )
    return TestClient(
        application,
        base_url="http://127.0.0.1:8000",
        client=kwargs.pop("client", ("127.0.0.1", 10000)),
        **kwargs,
    )


def test_unconfigured_default_app_never_returns_search_success_and_synthetic_app_does():
    with TestClient(
        create_app(), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 10000)
    ) as default:
        response = default.post("/search", json={"query": "예산"}, headers=AUTH)
        assert response.status_code in {404, 503}
        assert "results" not in response.json()
    with client_for() as client:
        response = client.post("/search", json={"query": "지난달 예산"}, headers=AUTH)
        assert response.status_code == 200
        assert len(response.json()["results"]) == 3
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/search/recent", headers=AUTH).json()[0]["query"] == "지난달 예산"


def test_stream_frames_are_parsed_then_results_then_answer():
    with client_for() as client:
        response = client.post(
            "/search",
            json={"query": "예산"},
            headers={**AUTH, "Accept": "application/x-ndjson"},
        )
        assert response.headers["content-type"].startswith("application/x-ndjson")
        assert [json.loads(line)["type"] for line in response.text.splitlines()] == [
            "parsed",
            "results",
            "answer",
        ]


@pytest.mark.parametrize(
    "headers,status",
    [
        ({}, 401),
        ({"Authorization": "Bearer bad"}, 401),
        ({**AUTH, "Origin": "null"}, 403),
        ({**AUTH, "Host": "outside.invalid"}, 403),
        ({**AUTH, "X-Forwarded-For": "127.0.0.1"}, 403),
    ],
)
def test_existing_auth_boundary_is_reused_for_search_and_history(headers, status):
    with client_for() as client:
        assert client.post("/search", json={"query": "예산"}, headers=headers).status_code == status
        assert client.get("/search/recent", headers=headers).status_code == status


def test_remote_clients_and_owner_injection_are_rejected():
    with client_for(client=("192.0.2.1", 10000)) as client:
        assert client.post("/search", json={"query": "예산"}, headers=AUTH).status_code == 403
    with client_for() as client:
        for payload in [
            {"query": "예산", "user_id": "other"},
            {"query": "예산", "account_id": "x"},
        ]:
            response = client.post("/search", json=payload, headers=AUTH)
            assert response.status_code == 422 and "other" not in response.text
        assert client.get("/search/recent?user_id=other", headers=AUTH).status_code == 422


def test_missing_ai_is_503_or_stream_error_and_never_fake_success():
    with client_for(parser=False) as client:
        response = client.post("/search", json={"query": "예산"}, headers=AUTH)
        assert (
            response.status_code == 503 and response.json()["error"]["code"] == "parser_unavailable"
        )
        response = client.post(
            "/search",
            json={"query": "예산"},
            headers={**AUTH, "Accept": "application/x-ndjson"},
        )
        frames = [json.loads(line) for line in response.text.splitlines()]
        assert [frame["type"] for frame in frames] == ["error"]
        assert frames[0]["data"]["code"] == "parser_unavailable"


@pytest.mark.parametrize("stream", [False, True])
def test_request_provider_scope_covers_both_parser_and_answer_and_is_reset(tmp_path, stream):
    from app.ai.selection import AISettingsStore, AIUpdate, Defaults, SelectedGeneration

    store = AISettingsStore(tmp_path / "ai", values={"OLLAMA_MODEL": "synthetic"})
    store.update(AIUpdate(mode="hybrid", defaults=Defaults(), external_consent=True))
    router = SelectedGeneration(store)
    seen = []

    class Parser(SyntheticParser):
        async def parse(self, **kwargs):
            seen.append(("parse", router.provider_for("search")))
            return await super().parse(**kwargs)

    class Answerer(SyntheticAnswerer):
        async def answer(self, **kwargs):
            seen.append(("answer", router.provider_for("search")))
            return await super().answer(**kwargs)

    with client_for() as client:
        client.app.state.ai_settings = store
        client.app.state.search_service.parser = Parser()
        client.app.state.search_service.answerer = Answerer()
        headers = {**AUTH, **({"Accept": "application/x-ndjson"} if stream else {})}
        assert (
            client.post(
                "/search", json={"query": "예산", "ai_provider": "claude"}, headers=headers
            ).status_code
            == 200
        )
        assert seen == [("parse", "claude"), ("answer", "claude")]
        seen.clear()
        assert client.post("/search", json={"query": "예산"}, headers=headers).status_code == 200
        assert seen == [("parse", "ollama"), ("answer", "ollama")]
