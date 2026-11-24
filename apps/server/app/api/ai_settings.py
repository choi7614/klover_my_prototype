"""AI 설정·연결 검사도 기존 로컬 Bearer 인증을 통과해야 한다."""

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.ai.interfaces import GenerationRequest, ProviderCallError, ProvidersNotConfigured
from app.ai.selection import AISelectionError, AIState, AIUpdate, SelectedGeneration, selected
from app.api.errors import error_response
from app.api.mail_read import authorize


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["ollama", "claude"]


class ProbeResult(BaseModel):
    status: Literal["reachable"] = "reachable"
    provider: Literal["ollama", "claude"]


def register_ai_settings(application):
    router = APIRouter(prefix="/settings/ai", tags=["AI 설정"], dependencies=[Depends(authorize)])

    def store(request):
        if request.query_params:
            raise HTTPException(422)
        result = getattr(request.app.state, "ai_settings", None)
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
        except (ProvidersNotConfigured, ProviderCallError, TimeoutError):
            return error_response(
                503,
                "ai_unavailable",
                "AI 연결에 실패했어요. 키·모델·실행 상태와 API 잔액을 확인하세요.",
            )
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
