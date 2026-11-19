"""F3 검색 라우터. 기존 인증 경계를 재사용하고 제공자를 명시적으로 주입한다."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.errors import error_response
from app.api.mail_read import authorize
from app.db.repositories.mail_query import MailAccountUnavailable
from app.schemas.common import ErrorResponse
from app.schemas.search import RecentSearch, SearchRequest, SearchResponse, SearchScope
from app.services.search_rules import SearchError

router = APIRouter(
    tags=["F3 검색"],
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 422, 500, 503)},
)


async def context(request: Request, repository: Annotated[object, Depends(authorize)]):
    service = getattr(request.app.state, "search_service", None)
    if service is None:
        raise HTTPException(503)
    try:
        owner = await run_in_threadpool(repository.session)
        scope = SearchScope(
            user_id=owner.user_id,
            account_id=owner.account_id,
            sync_started_at=owner.sync_started_at,
        )
    except (MailAccountUnavailable, SQLAlchemyError):
        raise HTTPException(503) from None
    if request.query_params:
        raise HTTPException(422)
    return service, scope


Context = Annotated[tuple, Depends(context)]


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, request: Request, dependency: Context):
    service, scope = dependency
    if "application/x-ndjson" in request.headers.get("accept", ""):

        async def stream():
            try:
                async for event in service.events(body, scope):
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except SearchError as error:
                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "data": {
                                "code": error.code,
                                "message": error.message,
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            except Exception:
                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "data": {
                                "code": "search_failed",
                                "message": "검색을 완료하지 못했어요.",
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        return StreamingResponse(stream(), media_type="application/x-ndjson")
    try:
        return await service.search(body, scope)
    except SearchError as error:
        return error_response(error.status, error.code, error.message)


@router.get("/search/recent", response_model=list[RecentSearch])
async def recent(dependency: Context):
    service, scope = dependency
    return await run_in_threadpool(service.recent_repository.recent, scope)


def register_search_api(application):
    """라우터와 개인 응답 캐시 정책을 등록한다. 제공자는 조립부에서 별도로 주입한다."""
    application.include_router(router)

    @application.middleware("http")
    async def private_search(request: Request, call_next):
        if request.url.path != "/search" and not request.url.path.startswith("/search/"):
            return await call_next(request)
        try:
            response = await call_next(request)
        except Exception:
            response = error_response(503, "search_unavailable", "검색 저장소를 확인해 주세요.")
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "X-Accel-Buffering": "no",
            }
        )
        return response
