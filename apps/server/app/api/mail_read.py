"""로컬 운영자의 읽기 API. Bearer 토큰은 Electron main만 읽고 전송한다."""

import secrets
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError

from app.api.errors import error_response
from app.db.repositories.mail_query import InvalidMailCursor, MailAccountUnavailable
from app.schemas.common import ErrorResponse
from app.schemas.mail_api import LocalSession, MailDetail, MailPage

bearer = HTTPBearer(auto_error=False, scheme_name="LocalMailBearer")


@dataclass(repr=False)
class MailAPIContext:
    token: str = field(repr=False)
    repository: object = field(repr=False)


def authorize(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    try:
        local = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    if (
        not local
        or request.url.hostname not in {"localhost", "127.0.0.1", "::1"}
        or request.headers.get("x-forwarded-for") is not None
        or request.headers.get("origin") is not None
    ):
        raise HTTPException(403)
    if credentials is None or len(request.headers.getlist("authorization")) != 1:
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
    context = getattr(request.app.state, "mail_api", None)
    if context is None:
        raise HTTPException(503)
    if len(credentials.credentials) > 128 or not secrets.compare_digest(
        credentials.credentials.encode(), context.token.encode()
    ):
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
    return context.repository


router = APIRouter(
    tags=["메일 조회"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
Repository = Annotated[object, Depends(authorize)]


def _read(operation):
    try:
        return operation()
    except InvalidMailCursor:
        raise HTTPException(422) from None
    except (MailAccountUnavailable, SQLAlchemyError):
        raise HTTPException(503) from None


@router.get("/auth/session", response_model=LocalSession)
def current_session(repository: Repository):
    """로컬 토큰의 소유 계정. Google 토큰·API 토큰은 응답에 포함하지 않는다."""
    return _read(repository.session)


@router.get("/mails", response_model=MailPage)
def list_mails(
    repository: Repository,
    request: Request,
    box: Literal["inbox"] = "inbox",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
):
    """받은 메일을 수신 시각·ID 내림차순으로 조회한다. 변경·동기화는 수행하지 않는다."""
    if set(request.query_params) - {"box", "limit", "cursor"} or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params
    ):
        raise HTTPException(422)
    return _read(lambda: repository.list(limit=limit, cursor=cursor))


@router.get("/mails/{mail_id}", response_model=MailDetail)
def read_mail(
    repository: Repository,
    mail_id: Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")],
):
    """소유 계정의 일반 텍스트 본문. 다른 계정 ID도 같은 404로 처리한다."""
    result = _read(lambda: repository.detail(mail_id))
    if result is None:
        raise HTTPException(404)
    return result


def register_mail_api(application):
    application.include_router(router)

    @application.middleware("http")
    async def private_responses(request: Request, call_next):
        private = request.url.path in {"/mails", "/auth/session"} or request.url.path.startswith(
            "/mails/"
        )
        if not private:
            return await call_next(request)
        try:
            response = await call_next(request)
        except Exception:
            response = error_response(500, "internal_error", "메일을 조회하지 못했습니다.")
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            }
        )
        return response
