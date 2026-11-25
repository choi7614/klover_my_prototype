import asyncio
import json

import pytest
from test_weekly_report import ACTOR, edit_request
from test_weekly_report import service as service

from app.ai.interfaces import ProviderCallError, ProviderIdentity, ProvidersNotConfigured
from app.ai.weekly_report import SharedWeeklyReportGenerator
from app.api.weekly_report import register_weekly_report_api
from app.db.repositories.mail_analysis import F1ReportMailRepository
from app.db.repositories.report_profile import F2ReportProfileRepository
from app.main import create_app
from app.schemas.profile_draft import Profile, ProfileState
from app.schemas.report import ReportPeriod
from app.schemas.weekly_report import GenerateWeeklyReport
from app.services.report import prepare_weekly_report_input
from app.services.weekly_report import WeeklyReportError
from app.services.weekly_report_runtime import WeeklyReportRuntime

PERIOD = ReportPeriod(start="2026-10-05", end="2026-10-09")


class SharedGenerationDouble:
    identity = ProviderIdentity(provider="f4-test-double", model="synthetic-json", mode="test")

    def __init__(self, response=None):
        self.calls = []
        self.response = response

    async def generate(self, request):
        self.calls.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        if self.response is not None:
            return self.response
        payload = json.loads(request.user_prompt)
        return json.dumps(
            {
                "sections": [
                    {
                        "name": name,
                        "items": [
                            {
                                "text": group["mails"][-1]["summary"]
                                or group["mails"][-1]["body_text"],
                                "evidence": group["mail_ids"],
                            }
                            for group in payload["groups"]
                        ]
                        if index == 0
                        else [],
                    }
                    for index, name in enumerate(payload["profile"]["report_sections"])
                ]
            },
            ensure_ascii=False,
        )


def test_f2_read_port_preserves_order_style_and_handles_absence():
    class Repository:
        state = ProfileState()
        seen = None

        def report_profile(self, *, user_id):
            self.seen = user_id
            return self.state

    repository = Repository()
    port = F2ReportProfileRepository(repository)
    assert asyncio.run(port.get_report_profile(user_id="user-a")) is None
    repository.state = ProfileState(
        exists=True,
        version=3,
        profile=Profile(
            name="홍길동",
            title="과장",
            org="재무팀",
            report_style="prose",
            report_recipient="이수진 팀장",
            report_sections=("issues", "highlights", "next_week", "ongoing"),
        ),
    )
    profile = asyncio.run(port.get_report_profile(user_id="user-a"))
    assert repository.seen == profile.user_id == "user-a"
    assert profile.report_sections == (
        "이슈·요청사항",
        "금주 주요 업무",
        "차주 계획",
        "진행 중인 업무",
    )
    assert profile.report_style == "prose" and profile.report_recipient == "이수진 팀장"


def test_common_ai_uses_weekly_purpose_schema_and_only_included_mail(service):
    source = asyncio.run(
        prepare_weekly_report_input(
            repository=service.mails,
            user_id=ACTOR.user_id,
            period=PERIOD,
        )
    )
    common = SharedGenerationDouble()
    adapter = SharedWeeklyReportGenerator(common, allow_test_provider=True)
    result = asyncio.run(
        adapter.generate(
            source=source, profile=service.profiles.profile, style="prose", recipient="팀장"
        )
    )
    assert adapter.mode == "test_double" and len(result.sections) == 4
    call = common.calls[0]
    assert call.purpose == "weekly_report" and "근거" in call.system_prompt
    assert call.response_schema["properties"]["sections"]
    payload = json.loads(call.user_prompt)
    assert payload["style"] == "prose" and payload["recipient"] == "팀장"
    identifiers = {mail["mail_id"] for group in payload["groups"] for mail in group["mails"]}
    assert len(identifiers) == 9 and "f4-09" not in identifiers and "other-user" not in identifiers
    assert "excluded" not in payload and "user_id" not in call.user_prompt


def test_common_test_provider_is_not_allowed_in_default_runtime():
    common = SharedGenerationDouble()
    with pytest.raises(ProvidersNotConfigured):
        SharedWeeklyReportGenerator(common)
    assert common.calls == []


@pytest.mark.parametrize(
    "response, code",
    [
        (ProvidersNotConfigured("SECRET_VALUE"), "ai_unavailable"),
        (ProviderCallError("SECRET_VALUE"), "ai_failed"),
        ("not-json", "invalid_report"),
        ('{"sections":[]}', "invalid_report"),
    ],
)
def test_shared_provider_failures_are_sanitized_and_do_not_replace_saved_edits(
    service, response, code
):
    async def scenario():
        initial = await service.generate(ACTOR, GenerateWeeklyReport())
        edited = await service.edit(
            ACTOR, initial.report_id, edit_request(initial, text="보존할 편집본")
        )
        service.generator = SharedWeeklyReportGenerator(
            SharedGenerationDouble(response), allow_test_provider=True
        )
        with pytest.raises(WeeklyReportError) as failure:
            await service.generate(
                ACTOR, GenerateWeeklyReport(regenerate=True, expected_revision=edited.revision)
            )
        assert failure.value.code == code and "SECRET_VALUE" not in str(failure.value)
        assert await service.get(ACTOR, initial.report_id) == edited

    asyncio.run(scenario())


def test_empty_f2_optional_fields_are_not_fabricated(service):
    service.profiles.profile = service.profiles.profile.model_copy(
        update={"org": "", "report_recipient": ""}
    )
    with pytest.raises(WeeklyReportError) as failure:
        asyncio.run(service.generate(ACTOR, GenerateWeeklyReport()))
    assert failure.value.code == "profile_incomplete" and service.generator.calls == 0
    document = asyncio.run(
        service.generate(ACTOR, GenerateWeeklyReport(recipient="직접 입력한 대상"))
    )
    assert document.recipient == "직접 입력한 대상"
    assert document.title.startswith("주간 업무 보고")


def test_runtime_reuses_f1_and_f2_without_creating_a_default_ai():
    actor = ACTOR.model_copy(update={"account_id": "account-a"})
    service = WeeklyReportRuntime(object()).for_actor(actor)
    assert isinstance(service.mails, F1ReportMailRepository)
    assert service.mails.repository.user_id == actor.user_id
    assert service.mails.repository.account_id == actor.account_id
    assert isinstance(service.profiles, F2ReportProfileRepository)
    assert service.generator is None
    with pytest.raises(WeeklyReportError, match="계정"):
        WeeklyReportRuntime(object()).for_actor(ACTOR)


def test_report_snapshots_are_isolated_between_accounts_of_the_same_user(service):
    async def scenario():
        a = ACTOR.model_copy(update={"account_id": "account-a"})
        b = ACTOR.model_copy(update={"account_id": "account-b"})
        first = await service.generate(a, GenerateWeeklyReport())
        for pending in (
            service.get(b, first.report_id),
            service.excluded(b, first.report_id),
            service.edit(b, first.report_id, edit_request(first, text="다른 계정의 수정")),
        ):
            with pytest.raises(WeeklyReportError) as failure:
                await pending
            assert failure.value.code == "not_found"
        other = await service.generate(b, GenerateWeeklyReport())
        assert other.report_id != first.report_id
        assert await service.get(a, first.report_id) == first

    asyncio.run(scenario())


def test_registration_is_idempotent_and_explicit_context_can_be_replaced(service):
    application = create_app()
    register_weekly_report_api(application)
    count = len(application.routes)
    register_weekly_report_api(application, service)
    assert len(application.routes) == count
    assert application.state.weekly_reports is service
