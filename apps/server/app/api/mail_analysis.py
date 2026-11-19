"""F1 전용 미등록 라우터. 공통 인증을 재사용하며 main·기존 조회 API는 바꾸지 않는다."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.api.mail_read import authorize
from app.db.repositories.mail_analysis import AnalysisRepository
from app.db.repositories.mail_query import MailAccountUnavailable
from app.schemas.mail_analysis import CategoryUpdate, CategoryUpdated


def create_analysis_router(engine: Engine) -> APIRouter:
    router = APIRouter(tags=["F1 분류 수정 (운영 앱 미등록)"])

    def scoped_repository(authorized: Annotated[object, Depends(authorize)]):
        try:
            # 소유자는 요청 본문·쿼리에서 받지 않고 검증된 기존 조회 세션에서만 가져온다.
            scope = authorized.session()
            return AnalysisRepository(engine, user_id=scope.user_id, account_id=scope.account_id)
        except (MailAccountUnavailable, SQLAlchemyError):
            raise HTTPException(503) from None

    @router.patch("/mails/{mail_id}/category", response_model=CategoryUpdated)
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
