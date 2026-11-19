import asyncio
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select

from app.api.mail_read import MailAPIContext
from app.api.weekly_report import register_weekly_report_api
from app.connectors.fixture import load_fixture_mails
from app.db.repositories.report_mail import InMemoryReportMailRepository
from app.db.repositories.weekly_report import (
    ReportConflictError,
    SQLWeeklyReportRepository,
    report_metadata,
    weekly_reports,
)
from app.main import create_app
from app.schemas.mail_api import LocalSession
from app.schemas.weekly_report import EditWeeklyReport, GenerateWeeklyReport, ReportActor
from app.services.report import ReportInputNotReadyError
from app.services.weekly_report import WeeklyReportError, WeeklyReportService
from app.testing.weekly_report import FixtureReportProfile, FixtureWeeklyGenerator

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures/mails/F4-weekly-report.json"
NOW = datetime(2026, 10, 12, tzinfo=UTC)
ACTOR = ReportActor(user_id="demo-hong", sync_started_at=NOW - timedelta(days=20))
OTHER = ReportActor(user_id="demo-other", sync_started_at=ACTOR.sync_started_at)
TOKEN = "T" * 43


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def service(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'f4-test.db'}")
    report_metadata.create_all(engine)
    service = WeeklyReportService(
        mails=InMemoryReportMailRepository(load_fixture_mails(FIXTURE)),
        profiles=FixtureReportProfile(),
        reports=SQLWeeklyReportRepository(engine),
        generator=FixtureWeeklyGenerator(),
        now=lambda: NOW,
    )
    yield service
    engine.dispose()


def generate(service, **overrides):
    return run(service.generate(ACTOR, GenerateWeeklyReport(**overrides)))


def edit_request(document, **item_changes):
    sections = [section.model_dump() for section in document.sections]
    sections[0]["items"][0].update(item_changes)
    return EditWeeklyReport(expected_revision=document.revision, sections=sections)


def test_defaults_use_previous_korean_work_week_and_profile_order(service):
    service.now = lambda: datetime(2026, 10, 11, 15, tzinfo=UTC)  # 한국 월요일 자정
    options = run(service.options(ACTOR))
    assert options.default_period.model_dump(mode="json") == {
        "start": "2026-10-05",
        "end": "2026-10-09",
    }
    document = generate(service)
    assert tuple(section.name for section in document.sections) == options.profile.report_sections
    assert document.style == "bullet" and document.recipient == "이수진 팀장"
    assert document.generation == "test_double"
    assert document.scope.model_dump() == {"total": 12, "grouped": 9, "groups": 6, "excluded": 3}


def test_save_reload_and_excluded_survive_repository_recreation(service):
    document = generate(service)
    engine = service.reports.engine
    engine.dispose()
    service.reports = SQLWeeklyReportRepository(create_engine(engine.url))
    assert run(service.get(ACTOR, document.report_id)) == document
    excluded = run(service.excluded(ACTOR, document.report_id))
    assert {item.mail.mail_id for item in excluded} == {"f4-09", "f4-10", "f4-12"}
    assert generate(service) == document
    assert service.generator.calls == 1
    service.reports.engine.dispose()


def test_profile_order_style_and_recipient_are_forwarded(service):
    service.profiles.profile = service.profiles.profile.model_copy(
        update={
            "report_sections": ("이슈·요청사항", "차주 계획", "금주 주요 업무"),
            "report_style": "prose",
        }
    )
    document = generate(service, recipient="김팀장")
    assert [section.name for section in document.sections] == [
        "이슈·요청사항",
        "차주 계획",
        "금주 주요 업무",
    ]
    assert document.style == "prose" and document.recipient == "김팀장"
    assert generate(service, template="bullet").style == "bullet"


def test_profile_missing_and_unavailable_ai_never_create_a_report(service):
    service.profiles.profile = service.profiles.profile.model_copy(
        update={"user_id": "someone-else"}
    )
    with pytest.raises(WeeklyReportError, match="프로필") as error:
        generate(service)
    assert error.value.code == "profile_missing"
    service.profiles = FixtureReportProfile()
    service.generator = None
    with pytest.raises(WeeklyReportError) as error:
        generate(service)
    assert error.value.code == "ai_unavailable"
    with service.reports.engine.connect() as connection:
        assert connection.scalar(select(weekly_reports.c.report_id)) is None


def test_one_week_readiness_blocks_generation(service):
    recent = ACTOR.model_copy(update={"sync_started_at": NOW - timedelta(days=6)})
    assert run(service.options(recent)).remaining_days == 1
    with pytest.raises(WeeklyReportError) as error:
        run(service.generate(recent, GenerateWeeklyReport()))
    assert error.value.code == "report_not_ready" and service.generator.calls == 0


@pytest.mark.parametrize("only_excluded", [False, True])
def test_empty_business_mail_does_not_call_ai(service, only_excluded):
    mails = load_fixture_mails(FIXTURE)
    service.mails = InMemoryReportMailRepository(
        [mail for mail in mails if mail.mail_id == "f4-09"] if only_excluded else []
    )
    document = generate(service)
    assert document.status == "empty" and document.generation == "none"
    assert document.scope.total == document.scope.excluded == int(only_excluded)
    assert all(not section.items for section in document.sections)
    assert service.generator.calls == 0


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_pending_and_failed_mail_are_not_summarized_or_hidden(service, status):
    mails = list(load_fixture_mails(FIXTURE))
    mails[0] = mails[0].model_copy(update={"analysis_status": status})
    service.mails = InMemoryReportMailRepository(mails)
    with pytest.raises(ReportInputNotReadyError) as error:
        generate(service)
    assert error.value.mail_ids == ("f4-01",)
    assert service.generator.calls == 0


@pytest.mark.parametrize(
    "evidence", [["missing"], ["other-user"], ["outside-before"], ["outside-after"], ["f4-09"]]
)
def test_invalid_generated_evidence_is_rejected_without_saving(service, evidence):
    original = service.generator.generate

    async def invalid(**kwargs):
        result = (await original(**kwargs)).model_dump()
        result["sections"][0]["items"][0]["evidence"] = evidence
        return result

    service.generator.generate = invalid
    with pytest.raises(WeeklyReportError) as error:
        generate(service)
    assert error.value.code == "invalid_evidence"
    with service.reports.engine.connect() as connection:
        assert connection.scalar(select(weekly_reports.c.report_id)) is None


@pytest.mark.parametrize(
    "mutation",
    ["empty_evidence", "duplicate_evidence", "blank_text", "section_order", "empty_items"],
)
def test_invalid_generated_shape_and_sections_are_rejected(service, mutation):
    original = service.generator.generate

    async def invalid(**kwargs):
        result = (await original(**kwargs)).model_dump()
        item = result["sections"][0]["items"][0]
        if mutation == "empty_evidence":
            item["evidence"] = []
        elif mutation == "duplicate_evidence":
            item["evidence"] = ["f4-01", "f4-01"]
        elif mutation == "blank_text":
            item["text"] = " "
        elif mutation == "section_order":
            result["sections"] = list(reversed(result["sections"]))
        else:
            result["sections"][0]["items"] = []
        return result

    service.generator.generate = invalid
    with pytest.raises(WeeklyReportError):
        generate(service)


def test_edit_and_reuse_keep_edited_text_and_evidence(service):
    document = generate(service)
    changed = run(
        service.edit(ACTOR, document.report_id, edit_request(document, text="검토 후 수정한 문장"))
    )
    assert changed.revision == 2 and changed.sections[0].items[0].text == "검토 후 수정한 문장"
    assert changed.sections[0].items[0].evidence == document.sections[0].items[0].evidence
    assert generate(service) == changed
    assert run(service.get(ACTOR, document.report_id)) == changed


def test_unknown_evidence_edit_and_stale_revision_preserve_saved_document(service):
    document = generate(service)
    with pytest.raises(WeeklyReportError):
        run(
            service.edit(ACTOR, document.report_id, edit_request(document, evidence=["other-user"]))
        )
    with pytest.raises(ValidationError):
        edit_request(document, evidence=[])
    changed = run(service.edit(ACTOR, document.report_id, edit_request(document, text="변경")))
    with pytest.raises(ReportConflictError):
        run(service.edit(ACTOR, document.report_id, edit_request(document, text="과거 수정")))
    assert run(service.get(ACTOR, document.report_id)) == changed


@pytest.mark.parametrize("failure", ["exception", "timeout", "bad_evidence", "pending"])
def test_regeneration_failure_preserves_edited_saved_report(service, failure):
    document = generate(service)
    edited = run(
        service.edit(ACTOR, document.report_id, edit_request(document, text="보존할 편집본"))
    )

    async def fail(**kwargs):
        if failure == "timeout":
            await asyncio.sleep(1)
        if failure == "bad_evidence":
            return {
                "sections": [
                    {
                        "name": name,
                        "items": [{"text": "검증", "evidence": ["bad-id"]}] if i == 0 else [],
                    }
                    for i, name in enumerate(service.profiles.profile.report_sections)
                ]
            }
        raise RuntimeError("민감한 내용이 응답에 노출되면 안 됩니다")

    service.generator.generate = fail
    service.timeout = 0.001
    if failure == "pending":
        mails = list(load_fixture_mails(FIXTURE))
        mails[0] = mails[0].model_copy(update={"analysis_status": "pending"})
        service.mails = InMemoryReportMailRepository(mails)
    with pytest.raises((WeeklyReportError, ReportInputNotReadyError)):
        generate(service, regenerate=True, expected_revision=edited.revision)
    assert run(service.get(ACTOR, document.report_id)) == edited


def test_regeneration_requires_matching_revision_and_keeps_report_identity(service):
    document = generate(service)
    with pytest.raises(ReportConflictError):
        generate(service, regenerate=True)
    updated = generate(service, regenerate=True, expected_revision=document.revision)
    assert updated.report_id == document.report_id and updated.revision == 2
    assert updated.created_at == document.created_at


def test_other_user_cannot_get_edit_or_read_excluded(service):
    document = generate(service)
    for operation in (
        service.get(OTHER, document.report_id),
        service.excluded(OTHER, document.report_id),
        service.edit(OTHER, document.report_id, edit_request(document, text="수정 시도")),
    ):
        with pytest.raises(WeeklyReportError) as error:
            run(operation)
        assert error.value.code == "not_found"
    assert run(service.get(ACTOR, document.report_id)) == document


def client(service, actor=ACTOR, configured=True):
    class SessionRepository:
        def session(self):
            return LocalSession(
                user_id=actor.user_id,
                account_id="synthetic",
                email="hong@example.test",
                sync_started_at=actor.sync_started_at,
            )

    application = create_app()
    application.state.mail_api = MailAPIContext(TOKEN, SessionRepository())
    register_weekly_report_api(application, service if configured else None)
    return TestClient(application, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 10101))


AUTH = {"Authorization": "Bearer " + TOKEN}


def test_feature_api_generate_read_edit_excluded_and_owner_isolation(service):
    with client(service) as http:
        options = http.get("/reports/weekly/options", headers=AUTH)
        assert options.status_code == 200
        response = http.post("/reports/weekly", json={}, headers=AUTH)
        assert response.status_code == 200, response.text
        report = response.json()
        path = "/reports/weekly/" + report["report_id"]
        assert http.get(path, headers=AUTH).json() == report
        assert len(http.get(path + "/excluded", headers=AUTH).json()) == 3
        report["sections"][0]["items"][0]["text"] = "API에서 편집한 문장"
        response = http.patch(
            path, json={"expected_revision": 1, "sections": report["sections"]}, headers=AUTH
        )
        assert response.status_code == 200 and response.json()["revision"] == 2
        assert (
            http.post("/reports/weekly", json={"user_id": "demo-other"}, headers=AUTH).status_code
            == 422
        )
    with client(service, OTHER) as http:
        for suffix in ("", "/excluded"):
            assert http.get(path + suffix, headers=AUTH).status_code == 404
        assert (
            http.patch(
                path, json={"expected_revision": 2, "sections": report["sections"]}, headers=AUTH
            ).status_code
            == 404
        )


@pytest.mark.parametrize(
    "headers, expected",
    [
        ({}, 401),
        ({"Authorization": "Bearer bad"}, 401),
        ({**AUTH, "Origin": "null"}, 403),
        ({**AUTH, "Host": "outside.invalid"}, 403),
    ],
)
def test_all_report_operations_reuse_existing_auth_checks(service, headers, expected):
    with client(service) as http:
        for method, path, body in (
            ("GET", "/reports/weekly/options", None),
            ("POST", "/reports/weekly", {}),
            ("GET", "/reports/weekly/id", None),
            ("GET", "/reports/weekly/id/excluded", None),
            ("PATCH", "/reports/weekly/id", {"expected_revision": 1, "sections": []}),
        ):
            response = http.request(method, path, headers=headers, json=body)
            assert response.status_code == expected
            assert response.headers["cache-control"] == "no-store"


def test_unconfigured_registration_and_errors_do_not_leak_details(service):
    with client(service, configured=False) as http:
        response = http.post("/reports/weekly", json={}, headers=AUTH)
        assert response.status_code == 503

    async def broken(**kwargs):
        raise RuntimeError("SECRET_MAIL_CONTENT")

    service.generator.generate = broken
    with client(service) as http:
        response = http.post("/reports/weekly", json={}, headers=AUTH)
        assert response.status_code == 502 and response.json()["error"]["code"] == "ai_failed"
        assert "SECRET_MAIL_CONTENT" not in response.text and TOKEN not in response.text


def test_production_main_routes_register_f4():
    paths = create_app().openapi()["paths"]
    assert "/reports/weekly" in paths and "/reports/weekly/options" in paths


def test_concurrent_edit_wins_over_an_in_flight_regeneration(service):
    async def scenario():
        document = await service.generate(ACTOR, GenerateWeeklyReport())
        original = service.generator.generate
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(**kwargs):
            entered.set()
            await release.wait()
            return await original(**kwargs)

        service.generator.generate = delayed
        task = asyncio.create_task(
            service.generate(ACTOR, GenerateWeeklyReport(regenerate=True, expected_revision=1))
        )
        await entered.wait()
        edited = await service.edit(
            ACTOR, document.report_id, edit_request(document, text="동시에 저장한 편집본")
        )
        release.set()
        with pytest.raises(ReportConflictError):
            await task
        assert await service.get(ACTOR, document.report_id) == edited

    run(scenario())


@pytest.mark.parametrize("database_file", [True, False])
def test_review_cli_refuses_existing_unmarked_files_without_modifying_them(tmp_path, database_file):
    path = tmp_path / "existing-file"
    if database_file:
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE user_data (content TEXT)")
            connection.execute("INSERT INTO user_data VALUES ('existing synthetic data')")
    else:
        path.write_text("기존 파일 보존 확인", encoding="utf-8")
    original = path.read_bytes()
    token = tmp_path / "synthetic-token"
    token.write_text(TOKEN)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli.review_weekly_report",
            "--fixture",
            str(FIXTURE),
            "--database",
            str(path),
            "--token-file",
            str(token),
            "--test-double",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert path.read_bytes() == original
    assert "검토 DB로 사용하지 않습니다" in result.stderr
