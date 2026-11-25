"""앱 보관함(FastAPI app.state)에 꽂는 이름을 한 곳에 모은다.

실행 명령(run_mail_api)이 서비스를 조립해 보관함에 꽂고, API 파일은 꺼내 쓴다.
이름을 문자열로 흩어 쓰면 오타가 나도 '연결 안 됨(503)'으로만 보이므로, 이름은 여기서만 정한다.
새 기능을 붙일 때: 아래 StateName에 이름을 추가하고, 조립은 set_state, 사용은 get_state로 한다.
tests/test_app_state_names.py가 app/ 안에서 이 목록에 없는 이름을 쓰면 실패하게 막는다.

테스트는 계속 application.state.<이름> = 객체 형태로 직접 꽂아도 된다(같은 보관함이다).
"""

from typing import Any

from fastapi import FastAPI, Request


class StateName:
    # 메일 조회·인증 (F0)
    MAIL_API = "mail_api"
    MAIL_SYNC = "mail_sync"
    HISTORY_IMPORT = "history_import"
    # 분석 (F1)
    MAIL_ANALYSIS_ENGINE = "mail_analysis_engine"
    MAIL_ANALYSIS_RUNNER = "mail_analysis_runner"
    # 프로필·답장 초안 (F2)
    PROFILE_DRAFT = "profile_draft"
    # 검색 (F3)
    SEARCH_SERVICE = "search_service"
    # 주간 보고 (F4)
    WEEKLY_REPORTS = "weekly_reports"
    # 제안·할 일·Calendar (F5)
    F5_SERVICE = "f5_service"
    # 공통
    AI_SETTINGS = "ai_settings"
    # 라우터 중복 등록 방지 표시
    F1_REGISTERED = "f1_registered"
    F2_REGISTERED = "f2_registered"
    F4_REGISTERED = "f4_registered"


KNOWN_NAMES = frozenset(v for k, v in vars(StateName).items() if not k.startswith("_"))


def _state_of(owner: Request | FastAPI) -> Any:
    return owner.app.state if isinstance(owner, Request) else owner.state


def get_state(owner: Request | FastAPI, name: str, default: Any = None) -> Any:
    """없으면 default(보통 None)를 돌려준다. 호출한 쪽이 '연결 안 됨'을 처리한다."""
    if name not in KNOWN_NAMES:
        raise KeyError(f"등록되지 않은 보관함 이름: {name}")
    return getattr(_state_of(owner), name, default)


def set_state(owner: Request | FastAPI, name: str, value: Any) -> None:
    if name not in KNOWN_NAMES:
        raise KeyError(f"등록되지 않은 보관함 이름: {name}")
    setattr(_state_of(owner), name, value)
