"""AI 설정·연결 검사도 기존 로컬 Bearer 인증을 통과해야 한다."""

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.ai.interfaces import GenerationRequest, ProviderCallError, ProvidersNotConfigured
from app.ai.selection import AISelectionError, AIState, AIUpdate, SelectedGeneration, selected
from app.api.errors import error_response
from app.api.mail_read import authorize
from app.api.state import StateName, get_state


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["ollama", "claude"]


class ProbeResult(BaseModel):
    status: Literal["reachable"] = "reachable"
    provider: Literal["ollama", "claude"]


# 연결 검사 실패 안내. 원인별로 고정 문장만 쓴다(키·응답 원문·환경 변수 이름은 담지 않는다).
PROBE_FAILURES = {
    "claude_key_missing": (
        "Claude API 키가 등록되지 않았어요. 키를 입력하고 저장한 뒤 다시 검사하세요."
    ),
    "claude_auth_failed": (
        "Claude API 키가 올바르지 않거나 사용 권한이 없어요. 키를 다시 입력해 저장하세요."
    ),
    "claude_model_not_found": "입력한 Claude 모델 ID를 찾지 못했어요. 모델 ID를 확인하세요.",
    "claude_rate_limited": (
        "Claude API 사용 한도에 걸렸어요. Anthropic Console에서 한도와 잔액을 확인하세요."
    ),
    "claude_timeout": "Claude 응답이 늦어요. 잠시 뒤 다시 검사하세요.",
    "claude_unreachable": "Claude API에 연결하지 못했어요. 인터넷 연결을 확인하세요.",
    "claude_bad_request": (
        "Claude가 요청을 거부했어요. 모델 ID가 이 계정에서 쓸 수 있는 최신 모델인지 확인하고, "
        "계속되면 Anthropic Console에서 계정 상태와 크레딧을 확인하세요."
    ),
    "claude_credit_low": (
        "Anthropic 계정의 크레딧(잔액)이 부족해요. Anthropic Console의 Plans & Billing에서 "
        "크레딧을 충전한 뒤 다시 검사하세요."
    ),
    "claude_effort_unsupported": (
        "이 Claude 모델은 응답 품질 설정을 지원하지 않아요. "
        "claude-sonnet-5-5 같은 최신 모델 ID를 쓰세요."
    ),
    "claude_format_unsupported": (
        "이 Claude 모델은 구조화된 JSON 출력을 지원하지 않아요. "
        "claude-sonnet-5-5 같은 최신 모델 ID를 쓰세요."
    ),
    "claude_refused": "Claude가 검사 요청에 답하지 않았어요. 잠시 뒤 다시 검사하세요.",
    "claude_truncated": "Claude 응답이 잘려서 확인하지 못했어요. 다시 검사하세요.",
    "claude_invalid_response": "Claude 응답을 읽지 못했어요. 모델 ID를 확인하고 다시 검사하세요.",
    "claude_error": "Claude 호출에 실패했어요. 잠시 뒤 다시 검사하세요.",
    "ollama_unreachable": (
        "로컬 AI(Ollama)에 연결하지 못했어요. Ollama 앱이 실행 중인지 확인하세요."
    ),
    "ollama_model_not_found": (
        "Ollama에 설정한 모델이 없어요. 'ollama pull 모델 이름'으로 받았는지 확인하세요."
    ),
    "ollama_timeout": (
        "로컬 AI 응답이 늦어요. 처음 실행이면 모델을 올리는 데 "
        "시간이 걸리니 잠시 뒤 다시 검사하세요."
    ),
    "ollama_bad_request": "Ollama가 요청을 거부했어요. Ollama를 최신으로 올린 뒤 다시 검사하세요.",
    "ollama_error": "로컬 AI 호출에 실패했어요. Ollama 상태를 확인하세요.",
    "ollama_invalid_response": "로컬 AI 응답을 읽지 못했어요. Ollama 버전을 확인하세요.",
    "ai_not_configured": "이 AI는 아직 설정되지 않았어요. 설정을 확인하세요.",
    "ai_timeout": "AI 응답이 제한 시간 안에 오지 않았어요. 잠시 뒤 다시 검사하세요.",
}


def probe_failure_code(settings, provider, error) -> str:
    if isinstance(error, TimeoutError):
        return "claude_timeout" if provider == "claude" else "ollama_timeout"
    code = getattr(error, "code", "")
    if code in PROBE_FAILURES:
        return code
    if isinstance(error, ProvidersNotConfigured):
        if provider == "claude" and not (
            settings.read().get("api_key") or settings.values().get("ANTHROPIC_API_KEY")
        ):
            return "claude_key_missing"
        return "ai_not_configured"
    return "claude_error" if provider == "claude" else "ollama_error"


def register_ai_settings(application):
    router = APIRouter(prefix="/settings/ai", tags=["AI 설정"], dependencies=[Depends(authorize)])

    def store(request):
        if request.query_params:
            raise HTTPException(422)
        result = get_state(request, StateName.AI_SETTINGS)
        if result is None:
            raise AISelectionError("메일 API 서버에서 AI 설정을 확인하세요.")
        return result

    @router.get("", response_model=AIState)
    def read(request: Request):
        return store(request).state()

    @router.put("", response_model=AIState)
    def update(body: AIUpdate, request: Request):
        return store(request).update(body)

    @router.post("/check", response_model=ProbeResult)
    async def check(body: Probe, request: Request):
        settings = store(request)
        try:
            with selected(settings, body.provider, fallback=False):
                await asyncio.wait_for(
                    SelectedGeneration(settings).generate(
                        GenerationRequest(
                            purpose="draft",
                            system_prompt="연결 검사입니다. JSON 하나만 반환하세요.",
                            user_prompt='{"test":"connection-only; no mail data"}',
                            response_schema={
                                "type": "object",
                                "properties": {"ok": {"type": "boolean"}},
                                "required": ["ok"],
                                "additionalProperties": False,
                            },
                        )
                    ),
                    timeout=120,
                )
        except (ProvidersNotConfigured, ProviderCallError, TimeoutError) as error:
            code = probe_failure_code(settings, body.provider, error)
            return error_response(503, code, PROBE_FAILURES[code])
        return ProbeResult(provider=body.provider)

    application.include_router(router)

    @application.exception_handler(AISelectionError)
    async def settings_error(_request, error):
        return error_response(503, "ai_settings_unavailable", str(error))

    @application.middleware("http")
    async def private_settings(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/settings/ai"):
            response.headers.update(
                {
                    "Cache-Control": "no-store",
                    "Pragma": "no-cache",
                    "Referrer-Policy": "no-referrer",
                    "X-Content-Type-Options": "nosniff",
                }
            )
        return response
