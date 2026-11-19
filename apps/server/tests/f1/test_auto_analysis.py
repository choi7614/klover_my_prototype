"""새 메일 자동 분석·분석 완료 알림 지점·앱 표시용 조회 검사. 합성 메일·테스트 대역만 쓴다."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.ai.interfaces import ProvidersNotConfigured
from app.api.mail_analysis import register_mail_analysis
from app.api.mail_read import MailAPIContext
from app.db.repositories.mail_analysis import AnalysisRepository
from app.main import create_app
from app.pipeline.analysis_hooks import AnalysisHooks, AnalysisOwner
from app.pipeline.auto_analysis import AutoAnalysis, build_auto_analysis
from app.schemas.mail_analysis import AnalysisResult
from tests.f1.support import CASES, ScriptedEmbedding, ScriptedGeneration
from tests.f1.test_storage import run, seed

OWNER = AnalysisOwner(user_id="f1-user-a", account_id="f1-account-a")


class LocalGeneration(ScriptedGeneration):
    """외부 전송이 없는(로컬 Ollama와 같은) 테스트 대역."""

    external_transfer = False


class ExternalGeneration(ScriptedGeneration):
    external_transfer = True


class FlakyGeneration(LocalGeneration):
    """처음 fail_calls번은 형식이 틀린 응답, 그 뒤로는 정답을 낸다."""

    def __init__(self, fail_calls):
        super().__init__()
        self.fail_calls = fail_calls

    async def generate(self, request):
        if self.fail_calls > 0:
            self.fail_calls -= 1
            self.calls.append(request)
            return "형식이 틀린 응답"
        return await super().generate(request)


def statuses(engine):
    with engine.connect() as connection:
        return dict(connection.execute(text("SELECT mail_id,analysis_status FROM mails")).all())


def runner_for(repository, generation=None, hooks=None):
    return AutoAnalysis(
        repository_factory=lambda: repository,
        providers=(generation or LocalGeneration(), ScriptedEmbedding()),
        hooks=hooks,
    )


# --- 분석 완료 알림 지점 (DB 불필요) ---------------------------------------------------------


def result_sample():
    return AnalysisResult.model_validate(CASES[0]["expected"])


def test_hooks_call_sync_and_async_callbacks_in_order_and_unregister():
    hooks = AnalysisHooks()
    calls = []

    def first(owner, mail_id, result):
        calls.append(("first", owner, mail_id, result.category))

    async def second(owner, mail_id, result):
        calls.append(("second", owner, mail_id, result.category))

    unregister = hooks.register(first)
    hooks.register(second)
    hooks.register(first)  # 같은 콜백은 한 번만
    assert len(hooks) == 2
    result = result_sample()
    assert asyncio.run(hooks.notify(OWNER, "f1-001", result)) == 0
    assert [call[0] for call in calls] == ["first", "second"]
    assert calls[0][1:] == (OWNER, "f1-001", result.category)
    unregister()
    calls.clear()
    asyncio.run(hooks.notify(OWNER, "f1-001", result))
    assert [call[0] for call in calls] == ["second"]


def test_hook_errors_and_timeouts_are_isolated(monkeypatch, caplog):
    import app.pipeline.analysis_hooks as module

    monkeypatch.setattr(module, "CALLBACK_TIMEOUT", 0.05)
    hooks = AnalysisHooks()
    reached = []

    def broken(*_):
        raise RuntimeError("합성 메일 본문 비밀")

    async def slow(*_):
        await asyncio.sleep(1)

    hooks.register(broken)
    hooks.register(slow)
    hooks.register(lambda *_: reached.append(True))
    assert asyncio.run(hooks.notify(OWNER, "f1-001", result_sample())) == 2
    assert reached == [True]
    assert "합성 메일 본문 비밀" not in caplog.text
    with pytest.raises(TypeError):
        hooks.register("not callable")


def test_runner_states_without_ai_or_with_external_ai_do_nothing():
    calls = []
    for providers, state in [
        (None, "not_configured"),
        ((ExternalGeneration(), ScriptedEmbedding()), "external_blocked"),
    ]:
        runner = AutoAnalysis(repository_factory=lambda: calls.append(1), providers=providers)
        assert runner.state == state
        assert runner.kick() is False
        assert asyncio.run(runner.drain()) == 0
        assert runner.retry(SimpleNamespace(requeue=lambda _: calls.append(2)), "x") == (
            "unavailable"
        )
        runner.close()
    assert calls == []


def test_build_without_ai_settings_is_not_configured():
    def missing():
        raise ProvidersNotConfigured("미설정")

    runner = build_auto_analysis(object(), lambda: None, loader=missing)
    assert runner.state == "not_configured"
    assert runner.kick() is False


def test_build_unknown_provider_is_treated_as_external():
    runner = build_auto_analysis(
        object(), lambda: None, loader=lambda: (ScriptedGeneration(), ScriptedEmbedding())
    )
    assert runner.state == "external_blocked"


# --- 실제 분리 DB -----------------------------------------------------------------------------


def test_process_pending_notifies_only_after_commit_and_only_done(f1_database):
    repository = seed(f1_database, cases=CASES[:2])
    seen = []

    def callback(owner, mail_id, result):
        # 알림 시점에는 이미 done으로 확정돼 있어야 한다.
        seen.append((owner, mail_id, result.mail_id, statuses(f1_database)[mail_id]))

    hooks = AnalysisHooks()
    hooks.register(callback)
    responses = ["틀린 응답", "또 틀린 응답"]
    llm = ScriptedGeneration(responses)
    first = run(repository, llm, mail_id=CASES[0]["mail"]["mail_id"], hooks=hooks)
    assert first.failed == 1 and seen == []
    second = run(repository, hooks=hooks)
    assert second.done == 1
    mail_id = CASES[1]["mail"]["mail_id"]
    assert seen == [(OWNER, mail_id, mail_id, "done")]


def test_hook_error_keeps_done_status(f1_database):
    repository = seed(f1_database)
    hooks = AnalysisHooks()
    hooks.register(lambda *_: (_ for _ in ()).throw(RuntimeError("x")))
    assert run(repository, hooks=hooks).done == 1
    assert set(statuses(f1_database).values()) == {"done"}


def test_kick_analyzes_new_gmail_mails_in_background_with_local_ai(f1_database):
    repository = seed(f1_database, cases=CASES[:3], source="gmail")
    hooks = AnalysisHooks()
    seen = []
    hooks.register(lambda owner, mail_id, result: seen.append(mail_id))
    runner = runner_for(repository, hooks=hooks)
    try:
        assert runner.kick() is True
        assert runner.wait_idle(20)
    finally:
        runner.close()
    assert set(statuses(f1_database).values()) == {"done"}
    assert sorted(seen) == sorted(case["mail"]["mail_id"] for case in CASES[:3])


def test_external_ai_leaves_gmail_mails_pending(f1_database):
    repository = seed(f1_database, source="gmail")
    llm = ExternalGeneration()
    runner = runner_for(repository, llm)
    assert runner.kick() is False
    runner.close()
    assert set(statuses(f1_database).values()) == {"pending"}
    assert llm.calls == []


def test_failure_is_marked_failed_and_retry_reanalyzes(f1_database):
    repository = seed(f1_database)
    mail_id = CASES[0]["mail"]["mail_id"]
    runner = runner_for(repository, FlakyGeneration(fail_calls=2))
    try:
        runner.kick()
        assert runner.wait_idle(20)
        assert statuses(f1_database)[mail_id] == "failed"
        assert runner.retry(repository, mail_id) == "queued"
        assert runner.wait_idle(20)
        assert statuses(f1_database)[mail_id] == "done"
        assert runner.retry(repository, mail_id) == "already_done"
        assert runner.retry(repository, "no-such-mail") == "not_found"
    finally:
        runner.close()


def test_runner_survives_storage_errors_and_keeps_pending(f1_database, caplog):
    def broken_factory():
        raise RuntimeError("postgresql://secret@db")

    seed(f1_database)
    runner = AutoAnalysis(
        repository_factory=broken_factory, providers=(LocalGeneration(), ScriptedEmbedding())
    )
    try:
        runner.kick()
        assert runner.wait_idle(20)
        runner.kick()  # 작업자가 죽지 않고 다음 신호도 받는다
        assert runner.wait_idle(20)
    finally:
        runner.close()
    assert set(statuses(f1_database).values()) == {"pending"}
    assert "secret" not in caplog.text


def test_views_follow_owner_status_and_hide_test_results_in_runtime(f1_database):
    repository = seed(f1_database, cases=CASES[:2])
    first, second = (case["mail"]["mail_id"] for case in CASES[:2])
    run(repository, mail_id=first)
    runtime = AnalysisRepository(f1_database, user_id="f1-user-a", account_id="f1-account-a")
    # 운영 저장소에서는 테스트 대역 결과를 보여 주지 않는다(가짜 결과 금지).
    hidden = runtime.views([first, second])
    assert [(view.mail_id, view.analysis_status, view.summary) for view in hidden] == [
        (first, "pending", None),
        (second, "pending", None),
    ]
    shown = repository.views([second, first, "missing", first])
    assert [view.mail_id for view in shown] == [second, first]
    done = shown[1]
    expected = CASES[0]["expected"]
    assert done.analysis_status == "done"
    assert done.category == expected["category"] and done.summary == expected["summary"]
    assert done.needs_reply == expected["needs_reply"]
    other = AnalysisRepository(f1_database, user_id="f1-user-a", account_id="other")
    assert other.views([first]) == ()


# --- HTTP ------------------------------------------------------------------------------------


def make_live(engine):
    """API 검사 전용: 테스트 스키마 안의 결과를 운영 표시 경로로 읽기 위해 모드 표시만 바꾼다."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE f1_mail_analysis SET llm_mode='live',embedding_mode='live'")
        )


@pytest.fixture
def http(f1_database):
    repository = seed(f1_database, cases=CASES[:2])
    application = create_app()
    register_mail_analysis(application, f1_database)
    application.state.mail_api = MailAPIContext(
        token="synthetic-api-token",
        repository=SimpleNamespace(
            session=lambda: SimpleNamespace(user_id="f1-user-a", account_id="f1-account-a")
        ),
    )
    with TestClient(
        application,
        base_url="http://localhost",
        client=("127.0.0.1", 43210),
        headers={"Authorization": "Bearer synthetic-api-token"},
    ) as session:
        yield SimpleNamespace(client=session, app=application, repository=repository)


def test_batch_and_detail_show_summary_tags_and_states(http, f1_database):
    first, second = (case["mail"]["mail_id"] for case in CASES[:2])
    run(http.repository, mail_id=first)
    make_live(f1_database)
    response = http.client.get("/mails/analysis/batch", params={"ids": [first, second]})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["auto_analysis"] == "not_connected"
    by_id = {item["mail_id"]: item for item in body["items"]}
    assert by_id[first]["analysis_status"] == "done"
    assert by_id[first]["summary"] == CASES[0]["expected"]["summary"]
    assert by_id[first]["category"] == CASES[0]["expected"]["category"]
    assert by_id[second] == {
        **by_id[second],
        "analysis_status": "pending",
        "summary": None,
        "category": None,
    }
    detail = http.client.get(f"/mails/{first}/analysis").json()
    assert detail["mail_id"] == first and detail["auto_analysis"] == "not_connected"
    assert detail["evidence_spans"] == CASES[0]["expected"]["evidence_spans"]
    # 응답에 원문·벡터·모델 정보는 없다.
    assert not {"body_text", "llm_model", "embedding", "llm_mode"} & set(detail)


def test_user_label_wins_and_shows_even_before_analysis(http):
    second = CASES[1]["mail"]["mail_id"]
    assert http.client.patch(f"/mails/{second}/category", json={"category": "notice"}).is_success
    item = http.client.get("/mails/analysis/batch", params={"ids": second}).json()["items"][0]
    assert item["analysis_status"] == "pending"
    assert item["category"] == "notice" and item["user_label"] == "notice"


def test_batch_and_detail_reject_bad_input_and_hide_other_owner(http):
    assert http.client.get("/mails/analysis/batch").status_code == 422
    assert http.client.get("/mails/analysis/batch", params={"ids": "../x"}).status_code == 422
    too_many = {"ids": [f"m{index}" for index in range(101)]}
    assert http.client.get("/mails/analysis/batch", params=too_many).status_code == 422
    extra = {"ids": "f1-001", "user_id": "other"}
    assert http.client.get("/mails/analysis/batch", params=extra).status_code == 422
    assert http.client.get("/mails/analysis/batch", params={"ids": "nope"}).json()["items"] == []
    assert http.client.get("/mails/nope/analysis").status_code == 404
    unauth = http.client.get("/mails/f1-001/analysis", headers={"Authorization": "Bearer wrong"})
    assert unauth.status_code == 401


def test_retry_endpoint(http, f1_database):
    first = CASES[0]["mail"]["mail_id"]
    run(http.repository, ScriptedGeneration(["x", "y"]), mail_id=first)
    # 자동 분석 미조립·AI 미설정이면 상태를 바꾸지 않고 안내한다.
    response = http.client.post(f"/mails/{first}/analysis/retry")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "analysis_unavailable"
    http.app.state.mail_analysis_runner = AutoAnalysis(
        repository_factory=lambda: http.repository, providers=None
    )
    assert http.client.post(f"/mails/{first}/analysis/retry").status_code == 503
    assert statuses(f1_database)[first] == "failed"
    detail = http.client.get(f"/mails/{first}/analysis").json()
    assert detail["analysis_status"] == "failed" and detail["failure_code"] == "invalid_response"
    assert detail["auto_analysis"] == "not_configured"

    runner = runner_for(http.repository)
    http.app.state.mail_analysis_runner = runner
    try:
        response = http.client.post(f"/mails/{first}/analysis/retry")
        assert response.status_code == 202
        assert response.json() == {"mail_id": first, "analysis_status": "pending"}
        assert runner.wait_idle(20)
        assert statuses(f1_database)[first] == "done"
        again = http.client.post(f"/mails/{first}/analysis/retry")
        assert again.status_code == 409
        assert http.client.post("/mails/nope/analysis/retry").status_code == 404
    finally:
        runner.close()


def test_existing_mail_routes_are_not_shadowed(http):
    paths = json.loads(http.client.get("/openapi.json").text)["paths"]
    assert {
        "/mails/analysis/batch",
        "/mails/{mail_id}/analysis",
        "/mails/{mail_id}/analysis/retry",
        "/mails/{mail_id}",
    } <= set(paths)
    # 기존 메일 상세는 그대로 동작한다(분석 경로가 가로채지 않음).
    assert http.client.get("/mails/f1-001").status_code != 405


def test_sync_endpoint_kicks_background_analysis_and_returns_first(f1_database, monkeypatch):
    """새로고침 → 저장 → 응답 → 백그라운드 분석 → done 흐름(패치 05의 조립과 같은 연결)."""
    import app.api.mail_sync as mail_sync
    from app.api.mail_sync import MailSyncContext, register_mail_sync

    repository = seed(f1_database, cases=CASES[:2], source="gmail")
    monkeypatch.setattr(
        mail_sync,
        "synchronize",
        lambda *_: {"saved": 2, "skipped": 0, "mode": "history", "token_refreshed": False},
    )

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    runner = runner_for(repository)
    application = create_app()
    register_mail_sync(application)
    application.state.mail_api = MailAPIContext(token="t" * 43, repository=object())
    application.state.mail_sync = MailSyncContext(object(), Client, after_sync=runner.kick)
    try:
        with TestClient(
            application, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1)
        ) as http:
            response = http.post("/mails/sync", headers={"Authorization": "Bearer " + "t" * 43})
        assert response.status_code == 200 and response.json()["saved"] == 2
        assert runner.wait_idle(20)
    finally:
        runner.close()
    assert set(statuses(f1_database).values()) == {"done"}
