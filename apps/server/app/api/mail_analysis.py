"""F1 분류 수정 라우터. 공통 인증을 재사용하며 기존 조회 API는 바꾸지 않는다.

운영 등록은 통합 채팅이 patches/F1/02-server-registration.patch로 한다
(main의 register_mail_analysis 호출 + run_mail_api의 엔진 주입).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.api.mail_read import authorize
from app.db.repositories.mail_analysis import AnalysisRepository
from app.db.repositories.mail_query import MailAccountUnavailable
from app.schemas.common import ErrorResponse
from app.schemas.mail_analysis import CategoryUpdate, CategoryUpdated


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
        mail_id: Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")],
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

    return router


def register_mail_analysis(application, engine: Engine | None = None):
    """운영 앱 등록. 개인 응답 헤더는 기존 /mails/ 경로 미들웨어가 붙인다."""
    if engine is not None:
        application.state.mail_analysis_engine = engine
    if getattr(application.state, "f1_registered", False):
        return
    application.state.f1_registered = True
    application.include_router(create_analysis_router())
