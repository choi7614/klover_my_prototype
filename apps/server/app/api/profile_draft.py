"""F2 등록 함수. 공통 app.main에는 승인 전 자동 연결하지 않는다."""

from dataclasses import dataclass, field
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.ai.f2_port import DraftAI, F2Error, RelatedMailSearch, UnavailableDraftAI
from app.api.ai_scope import ai_scope, execution_result
from app.api.errors import error_response
from app.api.mail_read import authorize
from app.api.state import StateName, get_state, set_state
from app.db.repositories.mail_query import MailAccountUnavailable
from app.db.repositories.profile_draft import F2Repository
from app.schemas.common import ErrorResponse
from app.schemas.profile_draft import (
    DraftCreate,
    DraftRevise,
    DraftSave,
    DraftState,
    Identifier,
    PreviewRequest,
    PreviewState,
    ProfileState,
    ProfileUpdate,
    StyleState,
)
from app.services.profile_draft import F2Service


@dataclass
class F2Context:
    repository: F2Repository
    ai: DraftAI = field(default_factory=UnavailableDraftAI)
    related: RelatedMailSearch | None = None


def service(request: Request, reader: Annotated[object, Depends(authorize)]):
    if request.query_params:
        raise HTTPException(422)
    context = get_state(request, StateName.PROFILE_DRAFT)
    if context is None:
        raise F2Error("f2_unavailable", 503, "프로필 저장소 연결이 준비되지 않았어요.")
    try:
        owner = reader.session()
    except MailAccountUnavailable:
        raise F2Error("mail_unavailable", 503, "연결한 메일 계정을 확인해 주세요.") from None
    return F2Service(
        repository=context.repository,
        ai=context.ai,
        related=context.related,
        mail_reader=reader,
        owner=owner,
    )


Service = Annotated[F2Service, Depends(service)]
router = APIRouter(
    tags=["F2 프로필·답장 초안"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 502, 503, 504)},
)


@router.get("/profile", response_model=ProfileState)
def profile(api: Service):
    return api.repository.profile(user_id=api.owner.user_id)


@router.put("/profile", response_model=ProfileState)
def save_profile(request: ProfileUpdate, api: Service):
    return api.repository.save_profile(user_id=api.owner.user_id, request=request)


@router.get("/profile/style", response_model=StyleState)
def style(api: Service):
    return api.repository.style(user_id=api.owner.user_id, include_inactive=True)


@router.delete("/profile/style", response_model=ProfileState)
def delete_style(api: Service):
    return api.repository.delete_style(user_id=api.owner.user_id)


@router.post("/profile/preview", response_model=PreviewState)
async def preview(request: PreviewRequest, api: Service, http: Request):
    with ai_scope(http, "ollama") as trace:
        return execution_result(await api.preview(request.profile), trace)


@router.post("/drafts", response_model=DraftState, status_code=201)
async def create_draft(request: DraftCreate, api: Service, http: Request):
    with ai_scope(http, request.ai_provider) as trace:
        return execution_result(await api.create(request), trace)


@router.get("/drafts/{draft_id}", response_model=DraftState)
def read_draft(draft_id: Identifier, api: Service):
    return api.draft(draft_id)


@router.patch("/drafts/{draft_id}", response_model=DraftState)
def save_draft(draft_id: Identifier, request: DraftSave, api: Service):
    return api.save(draft_id, request)


@router.post("/drafts/{draft_id}/revise", response_model=DraftState)
async def revise_draft(draft_id: Identifier, request: DraftRevise, api: Service, http: Request):
    with ai_scope(http, request.ai_provider) as trace:
        return execution_result(await api.revise(draft_id, request), trace)


def register_profile_draft(application):
    if get_state(application, StateName.F2_REGISTERED, False):
        return
    set_state(application, StateName.F2_REGISTERED, True)
    application.include_router(router)

    @application.exception_handler(F2Error)
    async def f2_error(_request, error):
        return error_response(error.status, error.code, error.message)

    @application.middleware("http")
    async def private_f2_response(request, call_next):
        if request.url.path not in {"/profile", "/drafts"} and not request.url.path.startswith(
            ("/profile/", "/drafts/")
        ):
            return await call_next(request)
        try:
            response = await call_next(request)
        except SQLAlchemyError:
            response = error_response(503, "storage_unavailable", "프로필 저장소를 확인해 주세요.")
        except Exception:
            response = error_response(500, "internal_error", "요청을 처리하지 못했어요.")
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            }
        )
        return response
