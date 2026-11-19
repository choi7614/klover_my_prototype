"""로컬 연결 도구 전용 HTML 경로. 앱 업무 API·다중 사용자 로그인은 아니다."""

import html
import re
import secrets
from ipaddress import ip_address
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from app.connectors.google_oauth import LoginAttempts, authorization_url
from app.google_config import ORIGIN, GoogleConnectionError
from app.main import create_app

COOKIE = "klover_google_browser"
PATH = "/auth/google"
HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
}


def page(message: str, status: int = 200, *, form: str = "") -> HTMLResponse:
    return HTMLResponse(
        '<!doctype html><html lang="ko"><meta charset="utf-8">'
        "<title>Klover Google 연결</title><h1>Klover Google 연결</h1>"
        f"<p>{html.escape(message)}</p>{form}</html>",
        status_code=status,
        headers=HEADERS,
    )


def is_local(request: Request) -> bool:
    try:
        return (
            request.headers.get("host") == "localhost:8000"
            and request.client is not None
            and ip_address(request.client.host).is_loopback
            and request.headers.get("x-forwarded-for") is None
        )
    except ValueError:
        return False


def create_google_app(settings, connector, repository) -> FastAPI:
    application = create_app()
    attempts = LoginAttempts()

    @application.get(PATH, response_class=HTMLResponse, tags=["로컬 Google 연결"])
    def connection_page(request: Request):
        if not is_local(request):
            return page("맥북의 localhost 주소에서 연결을 시작하세요.", 403)
        browser = secrets.token_urlsafe(32)
        form = (
            '<form method="post" action="/auth/google">'
            f'<input type="hidden" name="csrf" value="{browser}">'
            '<button type="submit">Google 계정 연결</button></form>'
        )
        response = page(
            "테스트 Gmail 계정의 읽기 권한을 요청합니다. 메일 수신·발송은 아직 실행하지 않습니다.",
            form=form,
        )
        # no-referrer는 폼 POST의 Origin도 null로 만들어 정상 출처 검증을 막는다.
        # 비밀 값이 없는 시작 화면은 같은 출처를 유지하고 콜백의 no-referrer는 보존한다.
        response.headers["Referrer-Policy"] = "same-origin"
        # 브라우저가 폼의 303 이동도 검사하므로 고정 Google 인증 출처만 허용한다.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; form-action 'self' https://accounts.google.com; "
            "frame-ancestors 'none'"
        )
        response.set_cookie(COOKIE, browser, max_age=600, httponly=True, samesite="lax", path=PATH)
        return response

    @application.post(
        PATH, status_code=303, response_class=RedirectResponse, tags=["로컬 Google 연결"]
    )
    async def begin(request: Request):
        if not is_local(request) or request.headers.get("origin") != ORIGIN:
            return page("이 연결 요청을 허용하지 않았습니다. 처음 화면에서 다시 시작하세요.", 403)
        if (
            request.headers.get("content-type", "").split(";")[0]
            != "application/x-www-form-urlencoded"
        ):
            return page("연결 요청 형식을 확인하세요.", 400)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return page("연결 요청 형식을 확인하세요.", 400)
        try:
            values = parse_qs(body.decode(), strict_parsing=True)
            csrf = values.get("csrf", [])
            browser = request.cookies.get(COOKIE, "")
            if (
                len(csrf) != 1
                or not re.fullmatch(r"[A-Za-z0-9_-]{43}", browser)
                or not re.fullmatch(r"[A-Za-z0-9_-]{43}", csrf[0])
                or not secrets.compare_digest(csrf[0], browser)
            ):
                raise ValueError
            state, verifier = attempts.begin(browser)
        except (ValueError, UnicodeError):
            return page("연결 요청이 만료됐습니다. 처음 화면에서 다시 시작하세요.", 400)
        return RedirectResponse(
            authorization_url(settings, state, verifier), status_code=303, headers=HEADERS
        )

    @application.get(PATH + "/callback", response_class=HTMLResponse, tags=["로컬 Google 연결"])
    def callback(request: Request):
        response = None
        try:
            if not is_local(request):
                return page("맥북의 localhost 주소에서 연결하세요.", 403)
            state_values = request.query_params.getlist("state")
            if len(state_values) != 1 or not 1 <= len(state_values[0]) <= 128:
                raise GoogleConnectionError("로그인 상태를 확인하지 못했습니다. 다시 연결하세요")
            browser = request.cookies.get(COOKIE, "")
            verifier = attempts.consume(state_values[0], browser)
            if "error" in request.query_params:
                raise GoogleConnectionError("Google 연결이 취소됐습니다. 원하면 다시 연결하세요")
            codes = request.query_params.getlist("code")
            if len(codes) != 1 or not 1 <= len(codes[0]) <= 4096:
                raise GoogleConnectionError("로그인 응답을 확인하지 못했습니다. 다시 연결하세요")
            email, tokens = connector.exchange(codes[0], verifier)
            repository.save(email, tokens)
            response = page(f"연결 확인 완료: {email}. 이 창을 닫아도 됩니다.")
        except GoogleConnectionError as error:
            response = page(str(error), 400)
        except SQLAlchemyError:
            response = page("저장하지 못했습니다. DB 실행 상태와 마이그레이션을 확인하세요.", 503)
        except Exception:
            # Google 코드·토큰·외부 응답이 예외 로그로 전달되지 않게 한다.
            response = page("연결을 완료하지 못했습니다. 설정을 확인하고 다시 시작하세요.", 500)
        response.delete_cookie(COOKIE, path=PATH)
        return response

    return application
