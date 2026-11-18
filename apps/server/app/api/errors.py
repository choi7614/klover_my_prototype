from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.common import ErrorDetail, ErrorResponse


def error_response(status: int, code: str, message: str, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, error: HTTPException) -> JSONResponse:
        code, message = {
            404: ("not_found", "요청한 경로를 찾을 수 없습니다."),
            405: ("method_not_allowed", "허용되지 않은 요청 방식입니다."),
        }.get(error.status_code, ("http_error", "요청을 처리할 수 없습니다."))
        return error_response(error.status_code, code, message, error.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        return error_response(422, "validation_error", "요청 형식을 확인해 주세요.")

    @app.exception_handler(Exception)
    async def handle_internal_error(_request: Request, _error: Exception) -> JSONResponse:
        # 입력값·메일 내용·예외 상세를 응답에 포함하지 않는다.
        return error_response(500, "internal_error", "서버에서 요청을 처리하지 못했습니다.")
