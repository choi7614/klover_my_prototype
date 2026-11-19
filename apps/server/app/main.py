"""DB·메일 계정·AI 키 없이 실행 가능한 공통 HTTP 서버."""

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.f5 import register_f5_api
from app.api.health import router as health_router
from app.api.mail_read import register_mail_api
from app.api.mail_sync import register_mail_sync
from app.api.profile_draft import register_profile_draft
from app.api.search import register_search_api
from app.api.weekly_report import register_weekly_report_api
from app.schemas.common import ErrorResponse


def create_app() -> FastAPI:
    application = FastAPI(
        title="Klover API",
        version="0.1.0",
        responses={
            422: {"model": ErrorResponse, "description": "요청 형식 오류"},
            500: {"model": ErrorResponse, "description": "서버 내부 오류"},
        },
    )
    register_error_handlers(application)
    application.include_router(health_router)
    register_mail_api(application)
    register_mail_sync(application)
    register_profile_draft(application)
    register_search_api(application)
    register_weekly_report_api(application)
    register_f5_api(application)
    return application


app = create_app()
