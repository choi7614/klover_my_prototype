"""실제 Gmail·외부 AI 없이 전용 PostgreSQL 스키마·합성 응답으로 F2를 검사한다."""

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database

from app.ai.f2_port import F2Error
from app.api.mail_read import MailAPIContext
from app.api.profile_draft import F2Context, register_profile_draft
from app.db.f2_models import DraftRecord, F2Base, StyleRecord
from app.db.models import User
from app.db.repositories.profile_draft import F2Repository
from app.main import create_app
from app.schemas.mail_api import LocalSession, MailDetail
from app.schemas.profile_draft import (
    GeneratedDraft,
    Profile,
    ProfileUpdate,
    StyleState,
)

TOKEN = "F" * 43
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
PROFILE = Profile(
    name="합성 사용자",
    title="과장",
    org="테스트팀",
    greeting="안녕하세요 🌿, 테스트팀입니다.",
    closing="감사합니다.\n합성 사용자 드림",
    signature="테스트팀 | test@example.invalid",
    report_sections=("issues", "highlights", "ongoing", "next_week"),
    report_recipient="합성 팀장",
    report_style="prose",
)


class SyntheticReader:
    def __init__(self, user_id="user-a"):
        self.user_id = user_id

    def session(self):
        return LocalSession(
            user_id=self.user_id,
            account_id=f"account-{self.user_id}",
            email=f"{self.user_id}@example.invalid",
            sync_started_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    def detail(self, mail_id):
        if mail_id not in {"original", "related"}:
            return None
        return MailDetail(
            mail_id=mail_id,
            subject="합성 자료 요청" if mail_id == "original" else "합성 지난 자료",
            from_addr="sender@example.invalid",
            from_name="합성 발신자",
            preview="합성 예시",
            body_text="합성 예시. 이전 지시를 무시하라는 문장도 데이터입니다.",
            received_at=datetime(2026, 11, 18, tzinfo=UTC),
            is_read=False,
            analysis_status="pending",
            to=[],
            cc=[],
        )


class SyntheticAI:
    """운영 코드에 연결하지 않는 합성 검사 전용 대역."""

    def __init__(self):
        self.calls = []
        self.output = None
        self.error = None

    async def generate(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        if self.output is not None:
            return self.output
        body = {"shorter": "확인했어요.", "politer": "확인해 주시면 감사하겠습니다."}.get(
            request.action, "자료를 확인한 뒤 회신하겠습니다."
        )
        return GeneratedDraft(
            body=body,
            directions=("확인 후 회신", "추가 정보 문의", "기한 조정 요청"),
            selected_direction=request.direction or "확인 후 회신",
        )


class SyntheticRelated:
    def __init__(self, ids=()):
        self.ids = ids
        self.calls = []

    async def find_ids(self, **values):
        self.calls.append(values)
        return self.ids


def application(repository=None, *, ai=None, user_id="user-a", related=None):
    app = create_app()
    register_profile_draft(app)
    app.state.mail_api = MailAPIContext(TOKEN, SyntheticReader(user_id))
    if repository is not None:
        context = F2Context(repository=repository, related=related)
        if ai is not None:
            context.ai = ai
        app.state.profile_draft = context
    return app


def client_for(repository=None, **options):
    return TestClient(
        application(repository, **options),
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 12345),
    )


@pytest.fixture
def repository(database):
    engine, _ = database
    F2Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([User(user_id="user-a"), User(user_id="user-b")])
    return F2Repository(engine)


def save_profile(client, *, profile=PROFILE, version=0, consent=False):
    return client.put(
        "/profile",
        headers=HEADERS,
        json={
            "profile": profile.model_dump(mode="json"),
            "expected_version": version,
            "consent_given": consent,
        },
    )


def create_draft(client):
    response = client.post("/drafts", json={"mail_id": "original"}, headers=HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    "field,value",
    [
        ("formality", -1),
        ("formality", 101),
        ("formality", True),
        ("formality", "70"),
        ("reply_length", "huge"),
        ("report_style", "html"),
        ("style_learning_enabled", "true"),
        ("report_sections", ["issues"]),
        ("report_sections", ["issues", "issues", "ongoing", "next_week"]),
        ("frequent_contacts", [" "]),
        ("frequent_contacts", ["a", "a"]),
        ("signature", "bad\x00value"),
        ("name", "a" * 101),
    ],
)
def test_profile_validation(field, value):
    with pytest.raises(ValidationError):
        Profile.model_validate({**PROFILE.model_dump(), field: value})


def test_profile_cannot_accept_owner_or_blank_name():
    with pytest.raises(ValidationError):
        Profile.model_validate({"user_id": "other"})
    with pytest.raises(ValidationError):
        ProfileUpdate(profile=Profile(name=" "), expected_version=0)


@pytest.mark.parametrize("path", ["/profile", "/profile/style", "/drafts/unknown"])
def test_auth_and_private_headers_without_database(path):
    with client_for() as client:
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
        response = client.get(path, headers={**HEADERS, "Origin": "null"})
        assert response.status_code == 403
        assert client.get(path, headers=HEADERS).status_code == 503


def test_save_requery_user_isolation_and_optimistic_lock(repository):
    with client_for(repository) as client, client_for(repository, user_id="user-b") as other:
        assert client.get("/profile", headers=HEADERS).json()["exists"] is False
        response = save_profile(client)
        assert response.status_code == 200 and response.json()["version"] == 1
        repository.engine.dispose()
        assert client.get("/profile", headers=HEADERS).json() == response.json()
        assert other.get("/profile", headers=HEADERS).json()["exists"] is False
        assert save_profile(client).status_code == 409
        assert client.get("/profile?user_id=user-b", headers=HEADERS).status_code == 422
        assert client.get("/profile", headers=HEADERS).json()["profile"] == PROFILE.model_dump(
            mode="json"
        )
        assert (
            repository.report_profile(user_id="user-a").profile.report_sections
            == PROFILE.report_sections
        )
        assert repository.report_profile(user_id="user-b").exists is False


def test_consent_disable_delete_and_exclusions(repository):
    enabled = PROFILE.model_copy(update={"style_learning_enabled": True})
    with client_for(repository) as client:
        assert save_profile(client, profile=enabled).json()["error"]["code"] == "consent_required"
        assert save_profile(client, profile=enabled, consent=True).status_code == 200
        state = client.get("/profile/style", headers=HEADERS).json()
        assert state["status"] == "unavailable" and state["analyzed_count"] == 0
        with Session(repository.engine) as session, session.begin():
            session.add(
                StyleRecord(
                    user_id="user-a",
                    payload=StyleState(
                        enabled=True,
                        status="ready",
                        analyzed_count=10,
                        phrases=("확인 부탁드립니다", "검토하겠습니다"),
                        traits=("결론 먼저",),
                    ).model_dump(mode="json"),
                )
            )
        excluded = enabled.model_copy(update={"excluded_phrases": ("확인 부탁드립니다",)})
        assert save_profile(client, profile=excluded, version=1).status_code == 200
        assert client.get("/profile/style", headers=HEADERS).json()["phrases"] == ["검토하겠습니다"]
        assert save_profile(client, version=2).status_code == 200
        assert client.get("/profile/style", headers=HEADERS).json()["phrases"] == []
        with Session(repository.engine) as session:
            assert session.get(StyleRecord, "user-a") is not None
        deleted = client.delete("/profile/style", headers=HEADERS)
        assert deleted.status_code == 200
        assert deleted.json()["profile"]["greeting"] == PROFILE.greeting
        assert deleted.json()["profile"]["style_learning_enabled"] is False
        with Session(repository.engine) as session:
            assert session.get(StyleRecord, "user-a") is None
        assert save_profile(client, profile=enabled, version=4).status_code == 422


def test_missing_ai_never_returns_synthetic_success(repository):
    with client_for(repository) as client:
        save_profile(client)
        for path, body in [
            ("/profile/preview", {"profile": PROFILE.model_dump(mode="json")}),
            ("/drafts", {"mail_id": "original"}),
        ]:
            result = client.post(path, json=body, headers=HEADERS)
            assert result.status_code == 503 and result.json()["error"]["code"] == "ai_unavailable"
        with Session(repository.engine) as session:
            assert list(session.scalars(select(DraftRecord))) == []


def test_preview_uses_unsaved_settings_and_no_actual_mail(repository):
    ai = SyntheticAI()
    with client_for(repository, ai=ai) as client:
        response = client.post(
            "/profile/preview", headers=HEADERS, json={"profile": PROFILE.model_dump(mode="json")}
        )
        assert response.status_code == 200
        assert response.json()["body"].startswith(PROFILE.greeting)
        assert ai.calls[0].purpose == "preview"
        assert ai.calls[0].original.mail_id == "preview-synthetic"
        assert client.get("/profile", headers=HEADERS).json()["exists"] is False


def test_profile_required_and_original_ownership_before_ai(repository):
    ai = SyntheticAI()
    with client_for(repository, ai=ai) as client:
        assert (
            client.post("/drafts", headers=HEADERS, json={"mail_id": "original"}).status_code == 409
        )
        save_profile(client)
        assert (
            client.post("/drafts", headers=HEADERS, json={"mail_id": "foreign"}).status_code == 404
        )
        assert ai.calls == []


def test_draft_profile_evidence_unicode_and_empty_context(repository):
    ai, related = SyntheticAI(), SyntheticRelated()
    with client_for(repository, ai=ai, related=related) as client:
        save_profile(client)
        draft = create_draft(client)
        assert draft["body"].startswith(PROFILE.greeting)
        assert draft["body"].endswith(PROFILE.signature)
        for evidence in draft["evidence"]:
            field = evidence["source"].split(".")[1]
            assert draft["body"][slice(*evidence["span"])] == getattr(PROFILE, field)
        assert draft["references"] == [] and draft["context_status"]["related"] == "empty"
        assert draft["context_status"]["analysis"] == "unavailable"
        assert related.calls[0]["user_id"] == "user-a"
        assert client.get("/drafts/" + draft["draft_id"], headers=HEADERS).json() == draft
        assert ai.calls[0].learned_phrases == ()
        assert ai.calls[0].original.action_items is None
        assert client.post("/mails/send", headers=HEADERS).status_code in {404, 405}


def test_only_authorized_reference_metadata_is_used(repository):
    ai = SyntheticAI()
    ai.output = {
        "body": "이전 자료를 참고합니다.",
        "directions": ["확인 후 회신", "추가 정보 문의"],
        "selected_direction": "확인 후 회신",
        "evidence": [{"span": [0, 5], "source": "mail:related"}],
    }
    with client_for(repository, ai=ai, related=SyntheticRelated(("related",))) as client:
        save_profile(client)
        draft = create_draft(client)
        assert draft["references"][0]["subject"] == "합성 지난 자료"
        assert draft["references"][0]["mail_id"] == "related"


@pytest.mark.parametrize(
    "evidence",
    [
        {"span": [0, 2], "source": "mail:foreign"},
        {"span": [-1, 2], "source": "mail:original"},
        {"span": [0, 999], "source": "mail:original"},
        {"span": [0, 2], "source": "profile.phrase"},
        {"span": [0, 2], "source": "profile.signature"},
    ],
)
def test_invalid_ai_evidence_is_rejected_and_not_saved(repository, evidence):
    ai = SyntheticAI()
    ai.output = {
        "body": "잘못된 결과",
        "directions": ["확인 후 회신", "추가 정보 문의"],
        "selected_direction": "확인 후 회신",
        "evidence": [evidence],
    }
    with client_for(repository, ai=ai) as client:
        save_profile(client)
        response = client.post("/drafts", headers=HEADERS, json={"mail_id": "original"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "invalid_ai_output"


@pytest.mark.parametrize("action", ["shorter", "politer", "rewrite"])
def test_revise_current_edits_and_new_profile_then_conflict(repository, action):
    ai = SyntheticAI()
    with client_for(repository, ai=ai) as client:
        save_profile(client)
        draft = create_draft(client)
        updated_profile = PROFILE.model_copy(update={"greeting": "새 인사"})
        save_profile(client, profile=updated_profile, version=1)
        response = client.post(
            f"/drafts/{draft['draft_id']}/revise",
            headers=HEADERS,
            json={
                "action": action,
                "body": "사용자가 고친 본문",
                "expected_version": 1,
                "direction": "추가 정보 문의",
            },
        )
        assert response.status_code == 200
        assert ai.calls[-1].current_body == "사용자가 고친 본문"
        assert ai.calls[-1].action == action and ai.calls[-1].direction == "추가 정보 문의"
        assert response.json()["body"].startswith("새 인사")
        assert response.json()["profile_version"] == 2
        stale = client.patch(
            f"/drafts/{draft['draft_id']}",
            headers=HEADERS,
            json={"body": "오래된 변경", "expected_version": 1},
        )
        assert stale.status_code == 409


def test_edits_survive_failure_and_other_user_cannot_read_or_revise(repository, caplog):
    ai = SyntheticAI()
    with (
        client_for(repository, ai=ai) as client,
        client_for(repository, user_id="user-b", ai=ai) as other,
    ):
        save_profile(client)
        draft = create_draft(client)
        path = "/drafts/" + draft["draft_id"]
        saved = client.patch(
            path, headers=HEADERS, json={"body": "내 편집 본문", "expected_version": 1}
        )
        assert saved.status_code == 200 and saved.json()["body"] == "내 편집 본문"
        ai.error = RuntimeError("synthetic-private-content")
        failed = client.post(
            path + "/revise",
            headers=HEADERS,
            json={"action": "rewrite", "body": "내 편집 본문", "expected_version": 2},
        )
        assert failed.status_code == 502
        assert "synthetic-private" not in failed.text + caplog.text
        assert client.get(path, headers=HEADERS).json()["body"] == "내 편집 본문"
        for method, suffix, body in [
            ("get", "", None),
            ("patch", "", {"body": "x", "expected_version": 2}),
            ("post", "/revise", {"action": "rewrite", "body": "x", "expected_version": 2}),
        ]:
            response = other.request(method, path + suffix, headers=HEADERS, json=body)
            assert response.status_code == 404


def test_related_foreign_mail_never_reaches_ai(repository):
    ai = SyntheticAI()
    with client_for(repository, ai=ai, related=SyntheticRelated(("foreign",))) as client:
        save_profile(client)
        assert (
            client.post("/drafts", headers=HEADERS, json={"mail_id": "original"}).status_code == 404
        )
        assert ai.calls == []


def test_timeout_returns_explicit_failure(repository, monkeypatch):
    class SlowAI:
        async def generate(self, _):
            await asyncio.sleep(1)

    monkeypatch.setattr("app.services.profile_draft.AI_TIMEOUT_SECONDS", 0.001)
    with client_for(repository, ai=SlowAI()) as client:
        save_profile(client)
        result = client.post("/drafts", headers=HEADERS, json={"mail_id": "original"})
        assert result.status_code == 504 and result.json()["error"]["code"] == "ai_timeout"


def test_feature_metadata_is_separate_and_registration_is_explicit():
    from fastapi import FastAPI

    from app.db.models import Base

    empty = FastAPI()
    assert "/profile" not in empty.openapi()["paths"]
    register_profile_draft(empty)
    empty.openapi_schema = None
    assert "/profile" in empty.openapi()["paths"]
    assert not {"profiles", "drafts", "style_learnings"} & set(Base.metadata.tables)


def test_private_storage_failure_does_not_expose_exception():
    class BrokenRepository:
        def profile(self, **_):
            raise F2Error("storage_unavailable", 503, "저장소를 확인해 주세요.")

    with client_for(BrokenRepository()) as client:
        response = client.get("/profile", headers=HEADERS)
        assert response.status_code == 503
        assert response.headers["cache-control"] == "no-store"
