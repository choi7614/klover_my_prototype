"""서버 검사 공통 격리. 개발자 .env의 실제 AI 설정이 검사에 섞이지 않게 한다."""

import pytest


@pytest.fixture(autouse=True)
def isolated_ai_settings(monkeypatch):
    # AI 제공자 설정은 각 검사가 값을 직접 넘길 때만 쓴다. 실제 호출·과금이 생기지 않는다.
    monkeypatch.setattr("app.ai.config.environment_values", lambda: {})
