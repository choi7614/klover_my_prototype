"""F1 라우터: 분류 수정, 앱 표시용 분석 결과 조회, 실패 분석 다시 시도.

공통 인증을 재사용하며 기존 조회 API(/mails, /mails/{id}) 응답 형식은 바꾸지 않는다.
운영 등록은 main의 register_mail_analysis(적용 완료)이고, 엔진은 run_mail_api가 넣는다.
자동 분석 작업자(app.state.mail_analysis_runner)는 patches/F1/05로 조립한다. 없으면 not_connected.
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.api.errors import error_response
from app.api.mail_read import authorize
from app.db.repositories.mail_analysis import AnalysisRepository
from app.db.repositories.mail_query import MailAccountUnavailable
from app.schemas.common import ErrorResponse
from app.schemas.mail_analysis import (
    AnalysisRetryResult,
    CategoryUpdate,
    CategoryUpdated,
    MailAnalysisBatch,
    MailAnalysisDetail,
)

MailId = Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]
MAIL_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,128}")


def _runner(request: Request):
    return getattr(request.app.state, "mail_analysis_runner", None)


def _auto_state(request: Request) -> str:
    runner = _runner(request)
    return "not_connected" if runner is None else runner.state


def create_analysis_router(engine: Engine | None = None) -> APIRouter:
    """engine을 주지 않으면 실행 명령이 넣어 둔 app.state.mail_analysis_engine을 쓴다."""
    router = APIRouter(tags=["F1 분류 수정"])

    def scoped_repository(request: Request, authorized: Annotated[object, Depends(authorize)]):
        bound = (
            engine
            if engine is not None
            else getattr(request.app.state, "mail_analysis_engine", None)
        )
        if bound is None:
            raise HTTPException(503)
        try:
            # 소유자는 요청 본문·쿼리에서 받지 않고 검증된 기존 조회 세션에서만 가져온다.
            scope = authorized.session()
            return AnalysisRepository(bound, user_id=scope.user_id, account_id=scope.account_id)
        except (MailAccountUnavailable, SQLAlchemyError):
            raise HTTPException(503) from None

    @router.patch(
        "/mails/{mail_id}/category",
        response_model=CategoryUpdated,
        summary="메일 분류 수정",
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def update_category(
        mail_id: MailId,
        body: CategoryUpdate,
        repository: Annotated[AnalysisRepository, Depends(scoped_repository)],
    ):
        try:
            changed = repository.set_category(mail_id, body.category)
        except SQLAlchemyError:
            raise HTTPException(503) from None
        if not changed:
            raise HTTPException(404)
        return CategoryUpdated(
            mail_id=mail_id, user_label=body.category, effective_category=body.category
        )

    # /mails/{mail_id}(2단 경로)와 겹치지 않도록 3단 경로를 쓴다.
    @router.get(
        "/mails/analysis/batch",
        response_model=MailAnalysisBatch,
        summary="메일 목록용 분석 결과 묶음 조회",
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def analysis_batch(
        request: Request,
        repository: Annotated[AnalysisRepository, Depends(scoped_repository)],
        ids: Annotated[list[str], Query(min_length=1, max_length=100)],
    ):
        if set(request.query_params) - {"ids"} or not all(
            MAIL_ID_PATTERN.fullmatch(value) for value in ids
        ):
            raise HTTPException(422)
        try:
            items = repository.views(ids)
        except SQLAlchemyError:
            raise HTTPException(503) from None
        return MailAnalysisBatch(items=items, auto_analysis=_auto_state(request))

    @router.get(
        "/mails/{mail_id}/analysis",
        response_model=MailAnalysisDetail,
        summary="메일 한 건의 분석 결과",
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def analysis_detail(
        request: Request,
        mail_id: MailId,
        repository: Annotated[AnalysisRepository, Depends(scoped_repository)],
    ):
        try:
            found = repository.views([mail_id])
        except SQLAlchemyError:
            raise HTTPException(503) from None
        if not found:
            raise HTTPException(404)
        return MailAnalysisDetail(**found[0].model_dump(), auto_analysis=_auto_state(request))

    @router.post(
        "/mails/{mail_id}/analysis/retry",
        response_model=AnalysisRetryResult,
        status_code=202,
        summary="분석 다시 시도",
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse, "description": "이미 분석 완료"},
            503: {"model": ErrorResponse, "description": "AI 미연결"},
        },
    )
    def retry_analysis(
        request: Request,
        mail_id: MailId,
        repository: Annotated[AnalysisRepository, Depends(scoped_repository)],
    ):
        runner = _runner(request)
        if runner is None or runner.state != "ready":
            return error_response(
                503,
                "analysis_unavailable",
                "AI가 연결되지 않아 지금은 다시 분석할 수 없습니다. 메일 원문은 그대로입니다.",
            )
        try:
            outcome = runner.retry(repository, mail_id)
        except SQLAlchemyError:
            raise HTTPException(503) from None
        if outcome == "not_found":
            raise HTTPException(404)
        if outcome == "already_done":
            return error_response(409, "already_analyzed", "이미 분석을 마친 메일입니다.")
        if outcome != "queued":
            return error_response(
                503,
                "analysis_unavailable",
                "AI가 연결되지 않아 지금은 다시 분석할 수 없습니다. 메일 원문은 그대로입니다.",
            )
        return AnalysisRetryResult(mail_id=mail_id, analysis_status="pending")

    return router


def register_mail_analysis(application, engine: Engine | None = None):
    """운영 앱 등록. 개인 응답 헤더는 기존 /mails/ 경로 미들웨어가 붙인다."""
    if engine is not None:
        application.state.mail_analysis_engine = engine
    if getattr(application.state, "f1_registered", False):
        return
    application.state.f1_registered = True
    application.include_router(create_analysis_router())
