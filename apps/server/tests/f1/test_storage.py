import asyncio
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.interfaces import ProvidersNotConfigured
from app.db.models import Mail, User
from app.db.repositories.mail import MailRepository
from app.db.repositories.mail_analysis import AnalysisRepository, F1ReportMailRepository
from app.pipeline.pending_analysis import process_pending
from app.schemas.report import ReportPeriod
from app.services.report import ReportInputNotReadyError, prepare_weekly_report_input
from tests.f1.support import CASES, ScriptedEmbedding, ScriptedGeneration, sample_mail

START = datetime(2026, 1, 1, tzinfo=UTC)


def seed(engine, *, cases=None, user_id="f1-user-a", account_id="f1-account-a", source="fixture"):
    cases = cases if cases is not None else [CASES[0]]
    with Session(engine) as session, session.begin():
        repository = MailRepository(session)
        if session.get(User, user_id) is None:
            repository.add_user(user_id=user_id)
        repository.add_account(
            user_id=user_id,
            account_id=account_id,
            source=source,
            email=account_id + "@example.invalid",
            sync_started_at=START,
        )
        for case in cases:
            mail = sample_mail(
                CASES.index(case), user_id=user_id, account_id=account_id, source=source
            )
            repository.store_received(
                user_id=user_id,
                account_id=account_id,
                mail_id=mail.mail_id,
                source_message_id="source-" + mail.mail_id,
                received_at=mail.received_at,
                from_addr=mail.from_addr,
                subject=mail.subject,
                body_text=mail.body_text,
                from_name=mail.from_name,
                to=[item.model_dump() for item in mail.to],
                cc=[item.model_dump() for item in mail.cc],
                thread_id=mail.thread_id,
            )
            session.get(Mail, mail.mail_id).body_html = "<p>보존할 합성 원문</p>"
    return AnalysisRepository(
        engine, user_id=user_id, account_id=account_id, allow_test_providers=True
    )


def run(repository, llm=None, embedding=None, **options):
    return asyncio.run(
        process_pending(
            repository, llm or ScriptedGeneration(), embedding or ScriptedEmbedding(), **options
        )
    )


def metadata(engine, mail_id="f1-001"):
    with engine.connect() as connection:
        return (
            connection.execute(
                text("""
            SELECT a.*,m.analysis_status,m.body_text,m.body_html FROM f1_mail_analysis a
            JOIN mails m ON m.mail_id=a.mail_id WHERE a.mail_id=:mail_id
        """),
                {"mail_id": mail_id},
            )
            .mappings()
            .one()
        )


def test_all_23_synthetic_mails_store_real_pgvector_and_no_duplicate(f1_database):
    repo = seed(f1_database, cases=CASES)
    llm, embedding = ScriptedGeneration(), ScriptedEmbedding()
    batch = run(repo, llm, embedding, limit=100)
    assert batch.done == 23 and batch.failed == 0
    assert len(llm.calls) == 23
    assert repo.readiness() == {"storage_ready": True, "pending": 0}
    assert run(repo, llm, embedding).outcomes == ()
    assert len(llm.calls) == 23
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_analysis")) == 23
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_chunks")) == 46
        assert (
            connection.scalar(
                text("""
            SELECT count(*) FROM f1_mail_chunks c JOIN f1_mail_analysis a
              ON c.mail_id=a.mail_id AND c.user_id=a.user_id AND c.account_id=a.account_id
            WHERE c.embedding_mode='test' AND a.llm_mode='test' AND vector_dims(c.embedding)=3
        """)
            )
            == 46
        )
        distance = connection.scalar(
            text("""
            SELECT embedding <=> '[0.1,0.2,1]'::vector FROM f1_mail_chunks LIMIT 1
        """)
        )
        assert abs(distance) < 0.00001
    row = metadata(f1_database)
    assert row["category"] == "work_request" and row["analysis_status"] == "done"
    assert row["body_text"] == CASES[0]["mail"]["body_text"]
    assert row["body_html"] == "<p>보존할 합성 원문</p>"


@pytest.mark.parametrize(
    "llm,embedding,code,attempts",
    [
        (ScriptedGeneration(["not-json", "still-not-json"]), None, "invalid_response", 2),
        (ScriptedGeneration([RuntimeError("private-response")]), None, "provider_error", 1),
        (None, ScriptedEmbedding(RuntimeError("private-embedding")), "embedding_error", 1),
        (None, ScriptedEmbedding([[0, 0, 0], [0, 0, 0]]), "embedding_error", 1),
    ],
)
def test_failure_is_persisted_without_losing_original(f1_database, llm, embedding, code, attempts):
    repo = seed(f1_database)
    result = run(repo, llm, embedding)
    assert result.failed == 1 and result.done == 0
    row = metadata(f1_database)
    assert row["analysis_status"] == "failed" and row["failure_code"] == code
    assert row["attempts"] == attempts and row["category"] is None and row["summary"] is None
    assert row["body_text"] == CASES[0]["mail"]["body_text"]
    assert row["body_html"] == "<p>보존할 합성 원문</p>"
    assert "private" not in json.dumps(dict(row), default=str)
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_chunks")) == 0


def test_one_retry_then_success_reaches_storage(f1_database):
    repo = seed(f1_database)
    result = run(repo, ScriptedGeneration(["{}", json.dumps(CASES[0]["expected"])]))
    assert result.done == 1 and metadata(f1_database)["attempts"] == 2


def test_correction_survives_success_reanalysis_and_failure(f1_database):
    repo = seed(f1_database)
    assert repo.set_category("f1-001", "notice")
    run(repo)
    row = metadata(f1_database)
    assert row["user_label"] == "notice" and row["category"] == "work_request"
    new_result = {**CASES[0]["expected"], "category": "meeting"}
    run(repo, ScriptedGeneration([json.dumps(new_result)]), mail_id="f1-001", reanalyze=True)
    row = metadata(f1_database)
    assert row["user_label"] == "notice" and row["category"] == "meeting"
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_chunks")) == 2
        assert connection.scalar(text("SELECT count(*) FROM f1_category_feedback")) == 1
        assert (
            connection.scalar(
                text("""
            SELECT count(*) FROM f1_mail_chunks WHERE category='notice'
        """)
            )
            == 2
        )
    assert repo.set_category("f1-001", "report_share")
    run(repo, ScriptedGeneration(["{}", "{}"]), mail_id="f1-001", reanalyze=True)
    row = metadata(f1_database)
    assert row["user_label"] == "report_share" and row["analysis_status"] == "failed"
    assert row["summary"] is None
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_chunks")) == 0


def test_user_and_account_isolation_and_feedback_scope(f1_database):
    owner = seed(f1_database)
    other_account = seed(f1_database, cases=[CASES[1]], account_id="f1-account-b")
    other_user = seed(f1_database, cases=[CASES[2]], user_id="f1-user-b", account_id="f1-account-c")
    assert owner.set_category("f1-001", "report_share")
    assert not other_account.set_category("f1-001", "notice")
    assert not other_user.set_category("f1-001", "notice")
    with owner.claim(mail_id="f1-002") as work:
        assert work is None
    with other_account.claim() as work:
        assert work.mail.mail_id == "f1-002" and work.examples() == ()
    with other_user.claim() as work:
        assert work.mail.mail_id == "f1-003" and work.examples() == ()
    llm = ScriptedGeneration()
    run(owner, llm)
    examples = json.loads(llm.calls[0].user_prompt)["category_examples"]
    assert examples == [{"subject": CASES[0]["mail"]["subject"], "category": "report_share"}]
    with f1_database.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text("""
                INSERT INTO f1_mail_analysis(mail_id,user_id,account_id)
                VALUES ('f1-002','f1-user-b','f1-account-c')
            """)
            )


def test_two_workers_skip_locked_pending_mail(f1_database):
    repo = seed(f1_database)
    with repo.claim() as first:
        assert first.mail.mail_id == "f1-001"
        with repo.claim() as second:
            assert second is None
    assert run(repo).done == 1


def test_correction_retry_is_idempotent_and_examples_only_keep_latest(f1_database):
    repo = seed(f1_database)
    assert repo.set_category("f1-001", "notice")
    assert repo.set_category("f1-001", "notice")
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_category_feedback")) == 1
    assert repo.set_category("f1-001", "report_share")
    llm = ScriptedGeneration()
    run(repo, llm)
    examples = json.loads(llm.calls[0].user_prompt)["category_examples"]
    assert examples == [{"subject": CASES[0]["mail"]["subject"], "category": "report_share"}]


def test_test_provider_flag_is_rejected_outside_f1_test_schema(f1_database):
    from sqlalchemy import create_engine

    outside = create_engine(
        f1_database.url.update_query_dict({"options": "-csearch_path=public"}), hide_parameters=True
    )
    try:
        with pytest.raises(ValueError, match="분리된 F1 테스트"):
            AnalysisRepository(
                outside, user_id="f1-user-a", account_id="f1-account-a", allow_test_providers=True
            )
    finally:
        outside.dispose()


def test_f4_reads_sent_and_exact_seoul_date_boundaries(f1_database):
    repo = seed(f1_database, cases=CASES[:4])
    period = ReportPeriod(start=date(2026, 11, 18), end=date(2026, 11, 18))
    with f1_database.begin() as connection:
        for mail_id, received_at in (
            ("f1-001", period.start_at),
            ("f1-002", period.end_before - timedelta(microseconds=1)),
            ("f1-003", period.end_before),
            ("f1-004", period.start_at - timedelta(microseconds=1)),
        ):
            connection.execute(
                text("UPDATE mails SET received_at=:at WHERE mail_id=:mail_id"),
                {"at": received_at, "mail_id": mail_id},
            )
        connection.execute(text("UPDATE mails SET direction='sent' WHERE mail_id='f1-002'"))
    rows = asyncio.run(
        F1ReportMailRepository(repo).list_received_and_sent(
            user_id="f1-user-a", start_at=period.start_at, end_before=period.end_before
        )
    )
    assert [row.mail_id for row in rows] == ["f1-001", "f1-002"]
    assert rows[1].direction == "sent"


def test_storage_error_rolls_back_metadata_chunks_and_status(f1_database):
    repo = seed(f1_database)
    inserts = 0

    def fail_second_chunk(conn, cursor, statement, parameters, context, executemany):
        nonlocal inserts
        if "INSERT INTO f1_mail_chunks" in statement:
            inserts += 1
            if inserts == 2:
                raise RuntimeError("synthetic-storage-failure")

    event.listen(f1_database, "before_cursor_execute", fail_second_chunk)
    try:
        with pytest.raises(RuntimeError, match="synthetic-storage-failure"):
            run(repo)
    finally:
        event.remove(f1_database, "before_cursor_execute", fail_second_chunk)
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_analysis")) == 0
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_chunks")) == 0
        assert connection.scalar(text("SELECT analysis_status FROM mails")) == "pending"
        assert (
            connection.scalar(text("SELECT body_text FROM mails")) == CASES[0]["mail"]["body_text"]
        )


def test_missing_or_test_provider_in_default_runtime_leaves_pending(f1_database):
    seed(f1_database)
    default = AnalysisRepository(f1_database, user_id="f1-user-a", account_id="f1-account-a")
    for providers in ((None, None), (ScriptedGeneration(), ScriptedEmbedding())):
        with pytest.raises(ProvidersNotConfigured):
            asyncio.run(process_pending(default, *providers))
    with f1_database.connect() as connection:
        assert connection.scalar(text("SELECT analysis_status FROM mails")) == "pending"
        assert connection.scalar(text("SELECT count(*) FROM f1_mail_analysis")) == 0


def test_gmail_content_needs_explicit_execution_option_and_never_syncs(f1_database):
    repo = seed(f1_database, source="gmail")
    llm = ScriptedGeneration()
    assert run(repo, llm).outcomes == ()
    assert llm.calls == []
    assert repo.readiness()["pending"] == 0
    assert repo.readiness(allow_gmail=True)["pending"] == 1
    # 합성 Gmail 모양 입력만 사용한다. 실제 커넥터·토큰·네트워크는 호출하지 않는다.
    assert run(repo, llm, allow_gmail=True).done == 1
    with f1_database.connect() as connection:
        account = connection.execute(
            text("SELECT sync_started_at,sync_cursor FROM mail_accounts")
        ).one()
        assert account.sync_started_at == START and account.sync_cursor is None
        assert connection.scalar(text("SELECT count(*) FROM google_credentials")) == 0


def test_f4_adapter_real_db_contract_boundaries_and_no_test_success_leak(f1_database):
    repo = seed(f1_database, cases=CASES[:4])
    adapter = F1ReportMailRepository(repo)
    period = ReportPeriod(start=date(2026, 11, 18), end=date(2026, 11, 18))
    with pytest.raises(ReportInputNotReadyError):
        asyncio.run(
            prepare_weekly_report_input(repository=adapter, user_id="f1-user-a", period=period)
        )
    run(repo)
    assert repo.set_category("f1-001", "notice")
    report = asyncio.run(
        prepare_weekly_report_input(repository=adapter, user_id="f1-user-a", period=period)
    )
    assert report.scope.total == 4 and report.scope.excluded == 1 and report.scope.grouped == 3
    assert report.excluded[0].mail.effective_category == "notice"
    assert (
        asyncio.run(
            adapter.list_received_and_sent(
                user_id="f1-user-b", start_at=period.start_at, end_before=period.end_before
            )
        )
        == ()
    )
    assert (
        asyncio.run(
            adapter.list_received_and_sent(
                user_id="f1-user-a",
                start_at=period.end_before,
                end_before=period.end_before + timedelta(days=1),
            )
        )
        == ()
    )
    default = F1ReportMailRepository(
        AnalysisRepository(f1_database, user_id="f1-user-a", account_id="f1-account-a")
    )
    rows = asyncio.run(
        default.list_received_and_sent(
            user_id="f1-user-a", start_at=period.start_at, end_before=period.end_before
        )
    )
    assert all(row.analysis_status == "pending" and row.summary is None for row in rows)
