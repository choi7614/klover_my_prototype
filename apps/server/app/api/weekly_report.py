"""F4 전용 경로. 운영 app.main에는 아직 등록하지 않는다."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.exc import SQLAlchemyError

from app.ai.interfaces import ProvidersNotConfigured
from app.api.ai_scope import ai_scope, execution_result
from app.api.errors import error_response
from app.api.mail_read import authorize
from app.api.state import StateName, get_state, set_state
from app.db.repositories.mail_query import MailAccountUnavailable
from app.db.repositories.weekly_report import ReportConflictError
from app.schemas.common import ErrorResponse
from app.schemas.report import ExcludedReportMail
from app.schemas.weekly_report import (
    EditWeeklyReport,
    GenerateWeeklyReport,
    ReportActor,
    WeeklyReportDocument,
    WeeklyReportOptions,
)
from app.services.report import ReportInputNotReadyError
from app.services.weekly_report import WeeklyReportError
from app.services.weekly_report_runtime import WeeklyReportRuntime


def register_weekly_report_api(application, service=None):
    if service is not None:
        set_state(application, StateName.WEEKLY_REPORTS, service)
    if get_state(application, StateName.F4_REGISTERED, False):
        return
    set_state(application, StateName.F4_REGISTERED, True)

    router = APIRouter(
        prefix="/reports/weekly",
        tags=["주간 보고"],
        responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 502, 503)},
    )

    def context(request: Request, repository: Annotated[object, Depends(authorize)]):
        if request.query_params:
            raise WeeklyReportError("validation_error", "요청 형식을 확인해 주세요.", 422)
        service = get_state(request, StateName.WEEKLY_REPORTS)
        if service is None:
            raise WeeklyReportError(
                "report_unavailable", "주간 보고가 아직 연결되지 않았습니다.", 503
            )
        try:
            session = repository.session()
        except (MailAccountUnavailable, SQLAlchemyError):
            raise WeeklyReportError(
                "session_unavailable", "연결된 계정을 확인해 주세요.", 503
            ) from None
        actor = ReportActor(
            user_id=session.user_id,
            account_id=session.account_id,
            sync_started_at=session.sync_started_at,
        )
        if isinstance(service, WeeklyReportRuntime):
            try:
                service = service.for_actor(actor)
            except ProvidersNotConfigured:
                raise WeeklyReportError(
                    "ai_unavailable", "보고서 AI가 아직 연결되지 않았습니다.", 503
                ) from None
        return service, actor

    Context = Annotated[tuple, Depends(context)]
    ReportID = Annotated[str, Path(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]

    @router.get("/options", response_model=WeeklyReportOptions)
    async def options(context: Context):
        service, actor = context
        return await service.options(actor)

    @router.post("", response_model=WeeklyReportDocument)
    async def generate(body: GenerateWeeklyReport, context: Context, request: Request):
        service, actor = context
        with ai_scope(request, body.ai_provider) as trace:
            return execution_result(await service.generate(actor, body), trace)

    @router.get("/{report_id}", response_model=WeeklyReportDocument)
    async def get(report_id: ReportID, context: Context):
        service, actor = context
        return await service.get(actor, report_id)

    @router.get("/{report_id}/excluded", response_model=tuple[ExcludedReportMail, ...])
    async def excluded(report_id: ReportID, context: Context):
        service, actor = context
        return await service.excluded(actor, report_id)

    @router.patch("/{report_id}", response_model=WeeklyReportDocument)
    async def edit(report_id: ReportID, body: EditWeeklyReport, context: Context):
        service, actor = context
        return await service.edit(actor, report_id, body)

    application.include_router(router)

    @application.middleware("http")
    async def private_reports(request: Request, call_next):
        if not (
            request.url.path == "/reports/weekly" or request.url.path.startswith("/reports/weekly/")
        ):
            return await call_next(request)
        try:
            response = await call_next(request)
        except WeeklyReportError as error:
            response = error_response(error.status, error.code, error.message)
        except ReportInputNotReadyError:
            response = error_response(
                409, "analysis_not_ready", "분석 대기·실패 메일을 먼저 확인해 주세요."
            )
        except ReportConflictError:
            response = error_response(
                409, "report_conflict", "저장본이 변경되었습니다. 편집 내용은 보존됩니다."
            )
        except SQLAlchemyError:
            response = error_response(503, "storage_unavailable", "보고서 저장소를 확인해 주세요.")
        except Exception:
            response = error_response(500, "internal_error", "보고서를 처리하지 못했습니다.")
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            }
        )
        return response
