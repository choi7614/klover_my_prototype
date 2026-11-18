import asyncio
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.connectors.fixture import load_fixture_mails
from app.db.repositories.report_mail import InMemoryReportMailRepository
from app.schemas.report import ReportMail, ReportPeriod
from app.services.report import ReportInputNotReadyError, prepare_weekly_report_input

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures/mails/F4-weekly-report.json"
PERIOD = ReportPeriod(start=date(2026, 10, 5), end=date(2026, 10, 9))


def make_mail(mail_id: str, **changes) -> ReportMail:
    return ReportMail.model_validate(
        {
            "mail_id": mail_id,
            "user_id": "demo-hong",
            "direction": "received",
            "received_at": "2026-10-05T09:00:00+09:00",
            "from_addr": "sender@example.test",
            "to": [{"addr": "hong@example.test", "name": "홍길동"}],
            "subject": "가짜 업무 메일",
            "body_text": "검증용 가짜 메일 본문입니다.",
            "analysis_status": "done",
            "category": "work_request",
            **changes,
        }
    )


def prepare(mails, *, user_id="demo-hong", period=PERIOD):
    return asyncio.run(
        prepare_weekly_report_input(
            repository=InMemoryReportMailRepository(mails), user_id=user_id, period=period
        )
    )


def test_weekly_fixture_preserves_evidence_exclusions_and_scope():
    result = prepare(load_fixture_mails(FIXTURE_PATH))

    assert result.scope.model_dump() == {"total": 12, "grouped": 9, "groups": 6, "excluded": 3}
    groups = [group.mail_ids for group in result.groups]
    assert ("f4-01", "f4-02", "f4-03") in groups
    assert ("f4-04", "f4-05") in groups
    assert ("f4-11",) in groups
    included_ids = [mail_id for group in result.groups for mail_id in group.mail_ids]
    assert set(included_ids) == {f"f4-{number:02d}" for number in (*range(1, 9), 11)}
    assert len(included_ids) == len(set(included_ids))
    assert {item.mail.mail_id: item.reason for item in result.excluded} == {
        "f4-09": "newsletter",
        "f4-10": "notice",
        "f4-12": "notice",
    }
    assert (
        result.groups[0].mails[0].body_text
        == "3분기 결산 1차 마감을 위해 부서별 자료를 확인해 주세요."
    )
    assert result.model_dump(mode="json")["groups"][0]["mail_ids"] == ["f4-01", "f4-02", "f4-03"]


def test_seoul_date_boundaries_include_both_directions_and_exclude_other_users():
    result = prepare(
        [
            make_mail("before", received_at="2026-10-04T14:59:59Z"),
            make_mail("start", received_at="2026-10-04T15:00:00Z"),
            make_mail("end", direction="sent", received_at="2026-10-09T14:59:59.999999Z"),
            make_mail("after", received_at="2026-10-09T15:00:00Z"),
            make_mail("foreign", user_id="demo-other"),
        ]
    )

    assert [group.mail_ids for group in result.groups] == [("start",), ("end",)]
    assert result.scope.total == 2


def test_single_day_period_includes_the_whole_day():
    result = prepare(
        [
            make_mail("start", received_at="2026-10-05T00:00:00+09:00"),
            make_mail("end", received_at="2026-10-05T23:59:59+09:00"),
            make_mail("next", received_at="2026-10-06T00:00:00+09:00"),
        ],
        period=ReportPeriod(start=date(2026, 10, 5), end=date(2026, 10, 5)),
    )

    assert result.scope.total == 2


def test_user_category_correction_works_in_both_directions():
    result = prepare(
        [
            make_mail("include", category="newsletter", user_label="work_request"),
            make_mail("exclude", category="work_request", user_label="notice"),
        ]
    )

    assert result.groups[0].mail_ids == ("include",)
    assert result.excluded[0].mail.mail_id == "exclude"
    assert result.excluded[0].reason == "notice"


@pytest.mark.parametrize(
    "changes",
    [{"analysis_status": "pending"}, {"analysis_status": "failed"}, {"category": None}],
)
def test_incomplete_business_mail_blocks_input_instead_of_being_silently_excluded(changes):
    with pytest.raises(ReportInputNotReadyError) as error:
        prepare([make_mail("ready"), make_mail("not-ready", **changes)])

    assert error.value.mail_ids == ("not-ready",)


def test_explicitly_excluded_notice_does_not_require_analysis():
    result = prepare(
        [make_mail("notice", category=None, user_label="notice", analysis_status="pending")]
    )

    assert result.scope.model_dump() == {"total": 1, "grouped": 0, "groups": 0, "excluded": 1}


def test_thread_and_project_connections_are_transitive_without_losing_mail():
    result = prepare(
        [
            make_mail("a", thread_id="thread-a"),
            make_mail("b", thread_id="thread-a", entities={"projects": ["결산"]}),
            make_mail("c", thread_id="thread-b", entities={"projects": ["결산", "감사"]}),
            make_mail("d", thread_id="thread-c", entities={"projects": ["감사"]}),
            make_mail("e"),
        ]
    )

    assert [group.mail_ids for group in result.groups] == [("a", "b", "c", "d"), ("e",)]
    assert result.scope.grouped == 5


def test_people_organizations_and_blank_keys_do_not_merge_work():
    result = prepare(
        [
            make_mail("a", entities={"orgs": ["재무팀"], "people": ["홍길동"]}),
            make_mail("b", entities={"orgs": ["재무팀"], "people": ["홍길동"]}),
            make_mail("c", thread_id=" ", entities={"projects": [" "]}),
            make_mail("d", thread_id=" ", entities={"projects": [" "]}),
        ]
    )

    assert [group.mail_ids for group in result.groups] == [("a",), ("b",), ("c",), ("d",)]


def test_thread_and_project_identifiers_have_separate_namespaces():
    result = prepare(
        [make_mail("a", thread_id="same-key"), make_mail("b", entities={"projects": ["same-key"]})]
    )

    assert result.scope.groups == 2


def test_excluded_mail_cannot_bridge_two_work_groups():
    result = prepare(
        [
            make_mail("a", thread_id="thread-a"),
            make_mail(
                "b", thread_id="thread-a", category="notice", entities={"projects": ["예산"]}
            ),
            make_mail("c", entities={"projects": ["예산"]}),
        ]
    )

    assert [group.mail_ids for group in result.groups] == [("a",), ("c",)]
    assert result.excluded[0].mail.mail_id == "b"


def test_result_is_stable_when_repository_order_changes():
    mails = load_fixture_mails(FIXTURE_PATH)

    assert prepare(mails).model_dump() == prepare(reversed(mails)).model_dump()


def test_no_mail_is_a_valid_empty_input():
    result = prepare([])

    assert result.groups == result.excluded == ()
    assert result.scope.model_dump() == {"total": 0, "grouped": 0, "groups": 0, "excluded": 0}


def test_reversed_period_and_missing_timezone_are_rejected():
    with pytest.raises(ValidationError, match="종료일"):
        ReportPeriod(start=date(2026, 10, 9), end=date(2026, 10, 5))
    with pytest.raises(ValidationError, match="timezone"):
        make_mail("naive", received_at=datetime(2026, 10, 5, 9))


def test_duplicate_mail_ids_and_empty_user_are_rejected():
    with pytest.raises(ValueError, match="중복"):
        prepare([make_mail("same"), make_mail("same")])
    with pytest.raises(ValueError, match="사용자 ID"):
        prepare([], user_id=" ")


@pytest.mark.parametrize(
    "mails",
    [
        [make_mail("foreign", user_id="demo-other")],
        [make_mail("outside", received_at="2026-10-10T00:00:00+09:00")],
        [make_mail("same"), make_mail("same")],
    ],
)
def test_service_rejects_a_repository_that_violates_the_query_contract(mails):
    class InvalidRepository:
        async def list_received_and_sent(self, **kwargs):
            return mails

    with pytest.raises(ValueError, match="조회 계약"):
        asyncio.run(
            prepare_weekly_report_input(
                repository=InvalidRepository(), user_id="demo-hong", period=PERIOD
            )
        )


def test_fixture_cli_prepares_input_without_an_http_server_or_ai():
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli.weekly_report_input",
            "--fixture",
            str(FIXTURE_PATH),
            "--user-id",
            "demo-hong",
            "--start",
            "2026-10-05",
            "--end",
            "2026-10-09",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(process.stdout)["scope"] == {
        "total": 12,
        "grouped": 9,
        "groups": 6,
        "excluded": 3,
    }


def test_fixture_requires_an_explicit_synthetic_marker(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"mails": []}', encoding="utf-8")

    with pytest.raises(ValidationError, match="synthetic"):
        load_fixture_mails(path)
