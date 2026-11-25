"""Claude API 어댑터(공식 anthropic SDK). 메일 내용이 Anthropic 서버로 전송된다.

- 보안 확인 전까지 테스트 데이터만 사용한다(AI_CLAUDE_TEST_DATA_ONLY=true 확인 필수).
- 비용 예측을 위해 거절 시 다른 모델로 다시 처리하는 기능(fallbacks)은 쓰지 않는다.
  거절·잘림은 고정 오류로 바꾸고, 각 기능의 실패 처리에 맡긴다.
- 키·메일 내용·응답 원문은 예외 메시지와 로그에 넣지 않는다.
"""

import re

from app.ai.config import ClaudeSettings
from app.ai.interfaces import (
    GenerationRequest,
    ProviderCallError,
    ProviderIdentity,
    ProvidersNotConfigured,
)
from app.ai.json_output import strict_schema

MESSAGES = {
    "claude_auth_failed": "Claude API 키를 확인하세요 (ANTHROPIC_API_KEY).",
    "claude_rate_limited": "Claude API 사용 한도에 걸렸어요. 잠시 뒤 다시 시도하세요.",
    "claude_timeout": "Claude 응답이 제한 시간 안에 오지 않았어요. 잠시 뒤 다시 시도하세요.",
    "claude_unreachable": "Claude API에 연결하지 못했어요. 인터넷 연결을 확인하세요.",
    "claude_model_not_found": "Claude 모델 이름을 확인하세요 (CLAUDE_MODEL).",
    "claude_bad_request": "Claude가 요청 형식을 거부했어요. 설정값(모델·effort)을 확인하세요.",
    "claude_credit_low": "Anthropic 크레딧(잔액)이 부족해요. 충전한 뒤 다시 시도하세요.",
    "claude_effort_unsupported": "이 Claude 모델은 응답 품질 설정(effort)을 지원하지 않아요.",
    "claude_format_unsupported": "이 Claude 모델은 구조화된 JSON 출력을 지원하지 않아요.",
    "claude_refused": "Claude가 이 요청에 답하지 않았어요(안전 거절).",
    "claude_truncated": "Claude 응답이 길이 제한에 걸려 잘렸어요. CLAUDE_MAX_TOKENS를 늘리세요.",
    "claude_invalid_response": "Claude 응답에서 결과 글을 찾지 못했어요.",
    "claude_error": "Claude 호출에 실패했어요. 잠시 뒤 다시 시도하세요.",
}


def _error(code: str, detail: str = "") -> ProviderCallError:
    return ProviderCallError(MESSAGES[code], code=code, detail=detail)


def safe_detail(error: Exception, secrets: tuple[str, ...] = ()) -> str:
    """Anthropic이 준 요청 거부 사유를 연결 검사 화면용으로 다듬는다(키 제거, 한 줄, 길이 제한).

    연결 검사는 메일 없는 합성 요청이라 사유에 메일 내용이 들어갈 수 없다.
    """
    text = str(getattr(error, "message", "") or "")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "…")
    text = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "…", text)
    return " ".join(text.split())[:200]


def _bad_request_code(error: Exception) -> str:
    """400의 원인을 고정 분류로만 구분한다. 응답 문장은 분류에만 쓰고 저장·전달하지 않는다."""
    text = str(getattr(error, "message", "") or "").lower()
    if "credit balance" in text or "billing" in text:
        return "claude_credit_low"
    if "effort" in text:
        return "claude_effort_unsupported"
    if any(word in text for word in ("output_config", "json_schema", "structured output")):
        return "claude_format_unsupported"
    return "claude_bad_request"


def _error_code(error: Exception) -> str:
    try:
        import anthropic
    except ImportError:
        return "claude_error"
    if isinstance(error, anthropic.BadRequestError):
        return _bad_request_code(error)
    # 더 구체적인 오류부터 확인한다(시간 초과는 연결 오류의 하위 종류).
    for kind, code in (
        (anthropic.AuthenticationError, "claude_auth_failed"),
        (anthropic.PermissionDeniedError, "claude_auth_failed"),
        (anthropic.NotFoundError, "claude_model_not_found"),
        (anthropic.RateLimitError, "claude_rate_limited"),
        (anthropic.BadRequestError, "claude_bad_request"),
        (anthropic.APITimeoutError, "claude_timeout"),
        (anthropic.APIConnectionError, "claude_unreachable"),
    ):
        if isinstance(error, kind):
            return code
    return "claude_error"


def create_client(settings: ClaudeSettings):
    try:
        import anthropic
    except ImportError:
        raise ProvidersNotConfigured(
            "anthropic 패키지가 설치되지 않았어요 (patches/F1의 의존성 패치 적용 후 uv sync)"
        ) from None
    return anthropic.AsyncAnthropic(
        api_key=settings.api_key,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )


class ClaudeGeneration:
    # 외부 전송 경로. F1 실행 명령은 이 제공자로 실제 Gmail 본문을 보내지 않는다.
    external_transfer = True

    def __init__(self, settings: ClaudeSettings, *, client=None):
        self.settings = settings
        self.client = client if client is not None else create_client(settings)
        self.identity = ProviderIdentity(
            provider="anthropic", model=settings.models["analysis"], mode="live"
        )
        # SDK 자체 재시도까지 기다릴 수 있게 바깥 시간 제한을 잡는다.
        self.call_timeout = settings.timeout_seconds * (settings.max_retries + 1) + 10

    def model_for(self, purpose: str) -> str:
        return self.settings.models[purpose]

    async def _create(self, request: GenerationRequest, *, with_effort: bool):
        output_config = {
            "format": {"type": "json_schema", "schema": strict_schema(request.response_schema)}
        }
        if with_effort:
            output_config = {"effort": self.settings.effort, **output_config}
        return await self.client.messages.create(
            model=self.model_for(request.purpose),
            max_tokens=self.settings.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.user_prompt}],
            output_config=output_config,
        )

    async def generate(self, request: GenerationRequest) -> str:
        try:
            try:
                response = await self._create(request, with_effort=True)
            except Exception as error:
                # effort를 지원하지 않는 모델이면 effort만 빼고 한 번 다시 보낸다.
                if _error_code(error) != "claude_effort_unsupported":
                    raise
                response = await self._create(request, with_effort=False)
        except Exception as error:
            raise _error(_error_code(error), safe_detail(error, (self.settings.api_key,))) from None
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            raise _error("claude_refused")
        if stop_reason == "max_tokens":
            raise _error("claude_truncated")
        text = next(
            (
                block.text
                for block in getattr(response, "content", None) or ()
                if getattr(block, "type", None) == "text"
            ),
            None,
        )
        if not isinstance(text, str):
            raise _error("claude_invalid_response")
        return text


async def list_models(api_key: str, *, timeout: float = 20.0) -> list[dict]:
    """이 키로 쓸 수 있는 모델 목록(Models API). 메일은 보내지 않고 키만 쓴다."""
    try:
        import anthropic
    except ImportError:
        raise ProvidersNotConfigured("anthropic 패키지가 설치되지 않았어요") from None
    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=1)
    try:
        page = await client.models.list(limit=100)
        return [
            {"id": str(model.id), "name": str(getattr(model, "display_name", "") or model.id)}
            for model in page.data
        ]
    except Exception as error:
        raise _error(_error_code(error), safe_detail(error, (api_key,))) from None
    finally:
        await client.close()
