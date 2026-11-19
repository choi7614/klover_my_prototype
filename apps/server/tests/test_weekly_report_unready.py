"""운영 조립(WeeklyReportRuntime)에서 F1 저장 표·실제 AI가 없을 때
500 대신 안내(503)를 주는지 확인한다."""

from sqlalchemy import create_engine

from app.services.weekly_report_runtime import WeeklyReportRuntime
from tests.test_weekly_report import AUTH, client


def test_runtime_without_f1_storage_or_ai_answers_503_not_500():
    # 표가 하나도 없는 임시 DB: F1 분석 표·F2 프로필 표·보고서 표가 모두 없는 상태를 흉내 낸다.
    runtime = WeeklyReportRuntime(create_engine("sqlite://"))
    with client(runtime) as http:
        for response in (
            http.get("/reports/weekly/options", headers=AUTH),
            http.post("/reports/weekly", json={}, headers=AUTH),
        ):
            assert response.status_code == 503, response.text
            assert response.json()["error"]["code"] in {"storage_unavailable", "ai_unavailable"}
