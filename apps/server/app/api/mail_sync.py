"""앱 새로고침용 Gmail 새 받은 메일 가져오기. CLI `gmail_mail sync`와 같은 수신 기능을 쓴다."""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.api.errors import error_response
from app.api.mail_read import authorize
from app.api.state import StateName, get_state
from app.db.repositories.mail_query import MailAccountUnavailable
from app.google_config import GoogleConnectionError
from app.schemas.common import ErrorResponse
from app.schemas.mail_api import MailSyncResult
from app.services.gmail_sync import synchronize

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class MailSyncContext:
    """실행 명령에서 조립한다. 저장소·Google 클라이언트 생성기는 응답·로그에 노출하지 않는다."""

    repository: object = field(repr=False)
    client_factory: Callable[[], object] = field(repr=False)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # 저장이 끝난 뒤 부르는 후속 작업(예: F1 자동 분석 시작 신호). 기다리지 않는 짧은 함수만 넣는다.
    after_sync: Callable[[], object] | None = field(default=None, repr=False)


router = APIRouter(
    tags=["메일 조회"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "이미 새 메일을 가져오는 중"},
        502: {"model": ErrorResponse, "description": "Gmail에서 가져오지 못함"},
        503: {"model": ErrorResponse},
    },
)


@router.post("/mails/sync", response_model=MailSyncResult)
def sync_mails(request: Request, _authorized: Annotated[object, Depends(authorize)]):
    """사용 시작 이후 도착한 받은편지함 메일만 저장한다. 이미 저장한 메일은 건너뛴다."""
    context = get_state(request, StateName.MAIL_SYNC)
    if context is None:
        raise HTTPException(503)
    # 같은 서버 안의 중복 요청은 기다리지 않고 바로 알린다.
    # 다른 프로세스(CLI)와는 저장소의 DB 행 잠금으로 직렬화된다.
    if not context.lock.acquire(blocking=False):
        return error_response(
            409, "sync_in_progress", "이미 새 메일을 가져오고 있습니다. 잠시 후 다시 시도해 주세요."
        )
    try:
        with context.client_factory() as client:
            result = MailSyncResult(**synchronize(context.repository, client))
    except GoogleConnectionError:
        # 실패한 배치는 저장소가 되돌린다. 외부 응답·메일 내용은 전달하지 않는다.
        return error_response(
            502,
            "gmail_unavailable",
            "Gmail에서 새 메일을 가져오지 못했습니다. 기존 메일은 그대로입니다.",
        )
    except (MailAccountUnavailable, SQLAlchemyError):
        raise HTTPException(503) from None
    finally:
        context.lock.release()
    # 새 메일이 없어도 신호를 준다(남은 pending도 이어서 분석). 실패해도 응답은 그대로다.
    if context.after_sync is not None:
        try:
            context.after_sync()
        except Exception as error:  # noqa: BLE001
            logger.warning("새 메일 후속 작업 시작 실패: %s", type(error).__name__)
    return result


def register_mail_sync(application):
    """공통 앱에 등록한다(main.py). 응답 보안 헤더는 mail_read의 /mails/ 미들웨어가 붙인다."""
    application.include_router(router)
