"""F1 분석 저장 → F2 프로필 → F4 공통 생성·저장을 분리 DB에서 확인한다."""

import asyncio
from datetime import UTC, datetime

import pytest
from test_weekly_report_adapters import SharedGenerationDouble

from app.db.repositories.profile_draft import F2Repository
from app.db.repositories.weekly_report import report_metadata
from app.schemas.profile_draft import Profile, ProfileUpdate
from app.schemas.weekly_report import GenerateWeeklyReport, ReportActor
from app.services.report import ReportInputNotReadyError
from app.services.weekly_report import WeeklyReportError
from app.services.weekly_report_runtime import WeeklyReportRuntime
from tests.f1.conftest import f1_database as f1_database
from tests.f1.support import CASES, ScriptedGeneration
from tests.f1.test_storage import START, run, seed

NOW = datetime(2026, 11, 23, tzinfo=UTC)


def save_profile(engine, user_id):
    F2Repository(engine).save_profile(
        user_id=user_id,
        request=ProfileUpdate(
            profile=Profile(
                name="홍길동",
                title="과장",
                org="재무팀",
                report_style="prose",
                report_recipient="이수진 팀장",
                report_sections=("issues", "highlights", "next_week", "ongoing"),
            ),
            expected_version=0,
        ),
    )


def actor(repository):
    return ReportActor(
        user_id=repository.user_id, account_id=repository.account_id, sync_started_at=START
    )


def test_real_f1_f2_contracts_generate_and_reload_without_changing_source(f1_database):
    repository = seed(f1_database)
    assert run(repository).done == 1
    save_profile(f1_database, repository.user_id)
    report_metadata.create_all(f1_database)
    common = SharedGenerationDouble()
    runtime = WeeklyReportRuntime(
        f1_database, generator=common, allow_test_provider=True, now=lambda: NOW
    )
    owner = actor(repository)

    async def scenario():
        service = runtime.for_actor(owner)
        document = await service.generate(owner, GenerateWeeklyReport())
        assert document.scope.total == document.scope.grouped == 1
        assert document.sections[0].name == "이슈·요청사항" and document.style == "prose"
        assert document.sections[0].items[0].evidence == ("f1-001",)
        assert document.generation == "test_double"
        f1_database.dispose()
        assert await runtime.for_actor(owner).get(owner, document.report_id) == document
        assert document.evidence_mails[0].body_text == CASES[0]["mail"]["body_text"]
        return document

    document = asyncio.run(scenario())
    assert len(common.calls) == 1
    assert document.recipient == "이수진 팀장"


def test_real_account_scope_keeps_reports_and_mail_separate(f1_database):
    first = seed(f1_database)
    second = seed(f1_database, cases=[CASES[1]], account_id="f1-account-b")
    run(first)
    run(second)
    save_profile(f1_database, first.user_id)
    report_metadata.create_all(f1_database)
    runtime = WeeklyReportRuntime(
        f1_database, generator=SharedGenerationDouble(), allow_test_provider=True, now=lambda: NOW
    )
    a, b = actor(first), actor(second)

    async def scenario():
        service_a, service_b = runtime.for_actor(a), runtime.for_actor(b)
        report_a = await service_a.generate(a, GenerateWeeklyReport())
        report_b = await service_b.generate(b, GenerateWeeklyReport())
        assert {mail.mail_id for mail in report_a.evidence_mails} == {"f1-001"}
        assert {mail.mail_id for mail in report_b.evidence_mails} == {"f1-002"}
        assert report_a.report_id != report_b.report_id
        with pytest.raises(WeeklyReportError) as failure:
            await service_b.get(b, report_a.report_id)
        assert failure.value.code == "not_found"

    asyncio.run(scenario())


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_actual_unfinished_f1_analysis_never_calls_shared_ai(f1_database, status):
    repository = seed(f1_database)
    if status == "failed":
        assert run(repository, ScriptedGeneration(["{}", "{}"])).failed == 1
    save_profile(f1_database, repository.user_id)
    report_metadata.create_all(f1_database)
    common = SharedGenerationDouble()
    runtime = WeeklyReportRuntime(
        f1_database, generator=common, allow_test_provider=True, now=lambda: NOW
    )
    owner = actor(repository)
    with pytest.raises(ReportInputNotReadyError):
        asyncio.run(runtime.for_actor(owner).generate(owner, GenerateWeeklyReport()))
    assert common.calls == []


def test_default_runtime_does_not_treat_stored_test_analysis_as_live(f1_database):
    repository = seed(f1_database)
    run(repository)
    save_profile(f1_database, repository.user_id)
    report_metadata.create_all(f1_database)
    owner = actor(repository)
    runtime = WeeklyReportRuntime(f1_database, now=lambda: NOW)
    with pytest.raises(ReportInputNotReadyError):
        asyncio.run(runtime.for_actor(owner).generate(owner, GenerateWeeklyReport()))


def test_default_runtime_also_rejects_cached_test_reports(f1_database):
    repository = seed(f1_database)
    run(repository)
    save_profile(f1_database, repository.user_id)
    report_metadata.create_all(f1_database)
    owner = actor(repository)
    review = WeeklyReportRuntime(
        f1_database, generator=SharedGenerationDouble(), allow_test_provider=True, now=lambda: NOW
    ).for_actor(owner)
    document = asyncio.run(review.generate(owner, GenerateWeeklyReport()))
    production = WeeklyReportRuntime(f1_database, now=lambda: NOW).for_actor(owner)
    with pytest.raises(WeeklyReportError) as failure:
        asyncio.run(production.get(owner, document.report_id))
    assert failure.value.code == "ai_unavailable"
