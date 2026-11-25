"""분리 테스트 앱용 F5 API. 공통 app.main에는 자동 등록하지 않는다."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.api.errors import error_response
from app.api.mail_read import authorize
from app.api.state import StateName, get_state, set_state
from app.db.repositories.mail_query import MailAccountUnavailable
from app.schemas.common import ErrorResponse
from app.schemas.f5 import (
    ApproveRequest,
    CalendarPayload,
    ConflictResult,
    EventPage,
    Principal,
    SuggestionPage,
    SuggestionView,
    TodoCreate,
    TodoPage,
    TodoUpdate,
    TodoView,
    VersionRequest,
)
from app.services.f5_errors import F5Error

router = APIRouter(
    tags=["F5 제안·할 일 (적용 전)"],
    responses={
        status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 500, 502, 503)
    },
)


def _owner(repository: Annotated[object, Depends(authorize)]):
    try:
        current = repository.session()
        return Principal(user_id=current.user_id, account_id=current.account_id)
    except (MailAccountUnavailable, SQLAlchemyError):
        raise HTTPException(503) from None


def _service(request: Request):
    service = get_state(request, StateName.F5_SERVICE)
    if service is None:
        raise HTTPException(503)
    return service


Owner = Annotated[Principal, Depends(_owner)]
Service = Annotated[object, Depends(_service)]
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=512)]


def _query(request, allowed):
    if set(request.query_params) - allowed or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params
    ):
        raise F5Error("invalid_query", 422)


@router.get("/suggestions", response_model=SuggestionPage)
def list_suggestions(
    request: Request,
    owner: Owner,
    service: Service,
    status: Literal["pending", "approved", "dismissed"] | None = None,
    mail_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    notified: bool | None = None,
    limit: Limit = 20,
    cursor: Cursor = None,
):
    _query(request, {"status", "mail_id", "notified", "limit", "cursor"})
    return service.repository.list(
        owner, status=status, mail_id=mail_id, notified=notified, limit=limit, cursor=cursor
    )


@router.get("/suggestions/{suggestion_id}", response_model=SuggestionView)
def get_suggestion(owner: Owner, service: Service, suggestion_id: str):
    return service.repository.get(owner, suggestion_id)


@router.post("/suggestions/{suggestion_id}/approve", response_model=SuggestionView)
def approve(owner: Owner, service: Service, suggestion_id: str, body: ApproveRequest):
    return service.approve(owner, suggestion_id, body)


@router.post("/suggestions/{suggestion_id}/reregister", response_model=SuggestionView)
def reregister(owner: Owner, service: Service, suggestion_id: str, body: VersionRequest):
    """등록한 일정을 사용자가 구글 캘린더에서 지웠을 때 다시 등록한다. 아직 있으면 만들지 않는다."""
    return service.reregister(owner, suggestion_id, body.version)


@router.post("/suggestions/{suggestion_id}/dismiss", response_model=SuggestionView)
def dismiss(owner: Owner, service: Service, suggestion_id: str, body: VersionRequest):
    return service.repository.dismiss(owner, suggestion_id, body.version)


@router.post("/suggestions/{suggestion_id}/conflicts", response_model=ConflictResult)
def conflicts(owner: Owner, service: Service, suggestion_id: str, body: CalendarPayload):
    return service.conflicts(owner, suggestion_id, body)


@router.get("/todos", response_model=TodoPage)
def list_todos(
    request: Request,
    owner: Owner,
    service: Service,
    status: Literal["open", "completed"] | None = None,
    limit: Limit = 20,
    cursor: Cursor = None,
):
    _query(request, {"status", "limit", "cursor"})
    return service.repository.list_todos(owner, status=status, limit=limit, cursor=cursor)


@router.post("/todos", response_model=TodoView)
def create_todo(owner: Owner, service: Service, body: TodoCreate):
    return service.repository.create_todo(owner, body)


@router.patch("/todos/{todo_id}", response_model=TodoView)
def update_todo(owner: Owner, service: Service, todo_id: str, body: TodoUpdate):
    return service.repository.update_todo(owner, todo_id, body)


@router.get("/suggestion-events", response_model=EventPage)
def events(request: Request, owner: Owner, service: Service, limit: Limit = 100):
    _query(request, {"limit"})
    return service.repository.events(owner, limit=limit)


@router.post("/suggestion-events/{event_id}/ack", status_code=204)
def ack(owner: Owner, service: Service, event_id: str):
    service.repository.ack_event(owner, event_id)
    return Response(status_code=204)


def register_f5_api(application, service=None):
    set_state(application, StateName.F5_SERVICE, service)
    application.include_router(router)

    @application.exception_handler(F5Error)
    async def f5_error(_request, error):
        return error_response(
            error.status, error.code, "제안을 처리하지 못했어요. 상태를 다시 확인해 주세요."
        )

    @application.middleware("http")
    async def private_f5_responses(request, call_next):
        private = any(
            request.url.path == prefix or request.url.path.startswith(prefix + "/")
            for prefix in ("/suggestions", "/todos", "/suggestion-events", "/calendar")
        )
        if not private:
            return await call_next(request)
        try:
            response = await call_next(request)
        except Exception:
            response = error_response(500, "internal_error", "제안을 처리하지 못했어요.")
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            }
        )
        return response
