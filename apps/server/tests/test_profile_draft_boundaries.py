"""F2 생성 중 변경과 기존 인증된 메일 저장소 연결 경계."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_mail_read_api import seeded
from test_postgresql_storage import database as database
from test_profile_draft import (
    HEADERS,
    PROFILE,
    SyntheticAI,
    application,
    client_for,
    create_draft,
    save_profile,
)
from test_profile_draft import (
    repository as repository,
)

from app.api.mail_read import MailAPIContext
from app.db.f2_models import DraftRecord, F2Base, StyleRecord
from app.db.repositories.profile_draft import F2Repository
from app.schemas.profile_draft import DraftSave, ProfileUpdate, StyleState


def test_generation_cannot_apply_old_consent_after_profile_changes(repository):
    class ConcurrentChange(SyntheticAI):
        async def generate(self, request):
            repository.save_profile(
                user_id="user-a",
                request=ProfileUpdate(profile=PROFILE, expected_version=1),
            )
            return await super().generate(request)

    enabled = PROFILE.model_copy(update={"style_learning_enabled": True})
    with client_for(repository, ai=ConcurrentChange()) as client:
        save_profile(client, profile=enabled, consent=True)
        response = client.post("/drafts", headers=HEADERS, json={"mail_id": "original"})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "profile_changed"
        with Session(repository.engine) as session:
            assert list(session.scalars(select(DraftRecord))) == []


def test_deleting_style_only_affects_authenticated_user(repository):
    with Session(repository.engine) as session, session.begin():
        for user in ["user-a", "user-b"]:
            session.add(
                StyleRecord(
                    user_id=user,
                    payload=StyleState(
                        enabled=True, status="ready", analyzed_count=10, phrases=("합성 표현",)
                    ).model_dump(mode="json"),
                )
            )
    with client_for(repository) as client:
        save_profile(client)
        assert client.delete("/profile/style", headers=HEADERS).status_code == 200
    with Session(repository.engine) as session:
        assert session.get(StyleRecord, "user-a") is None
        assert session.get(StyleRecord, "user-b") is not None


def test_concurrent_save_wins_over_inflight_revision(repository):
    ai = SyntheticAI()
    with client_for(repository, ai=ai) as client:
        save_profile(client)
        draft = create_draft(client)

        async def concurrent_save(request):
            previous = repository.draft(user_id="user-a", draft_id=draft["draft_id"])
            repository.save_draft(
                user_id="user-a",
                draft=previous.model_copy(update={"body": "더 최신의 사용자 편집", "version": 2}),
                expected_version=1,
            )
            return await SyntheticAI().generate(request)

        ai.generate = concurrent_save
        response = client.post(
            f"/drafts/{draft['draft_id']}/revise",
            headers=HEADERS,
            json=DraftSave(body="이전 사용자 편집", expected_version=1).model_dump()
            | {"action": "rewrite"},
        )
        assert response.status_code == 409
        assert (
            repository.draft(user_id="user-a", draft_id=draft["draft_id"]).body
            == "더 최신의 사용자 편집"
        )


def test_f2_can_reuse_existing_authenticated_mail_reader(database):
    from fastapi.testclient import TestClient

    engine, _, reader = seeded(database)
    F2Base.metadata.create_all(engine)
    repository = F2Repository(engine)
    app = application(repository, ai=SyntheticAI())
    from test_profile_draft import TOKEN

    app.state.mail_api = MailAPIContext(TOKEN, reader)
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345)) as client:
        assert save_profile(client).status_code == 200
        response = client.post("/drafts", headers=HEADERS, json={"mail_id": "m-a"})
        assert response.status_code == 201
        for foreign in ["private-other", "private-same-user", "old", "sent"]:
            denied = client.post("/drafts", headers=HEADERS, json={"mail_id": foreign})
            assert denied.status_code == 404


def test_missing_connected_account_is_explicit_preparation_failure(repository):
    from fastapi.testclient import TestClient

    from app.db.repositories.mail_query import MailAccountUnavailable

    class MissingAccount:
        def session(self):
            raise MailAccountUnavailable("synthetic-private-account")

    app = application(repository)
    from test_profile_draft import TOKEN

    app.state.mail_api = MailAPIContext(TOKEN, MissingAccount())
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345)) as client:
        response = client.get("/profile", headers=HEADERS)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "mail_unavailable"
        assert "synthetic-private" not in response.text


def test_excluded_phrase_cannot_be_used_without_evidence_either(repository):
    ai = SyntheticAI()
    with client_for(repository, ai=ai) as client:
        excluded = PROFILE.model_copy(update={"excluded_phrases": ("확인 부탁드립니다",)})
        save_profile(client, profile=excluded)
        ai.output = {
            "body": "확인 부탁드립니다",
            "directions": ["회신", "문의"],
            "selected_direction": "회신",
            "evidence": [],
        }
        response = client.post("/drafts", headers=HEADERS, json={"mail_id": "original"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "invalid_ai_output"
