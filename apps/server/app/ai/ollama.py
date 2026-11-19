"""이 컴퓨터의 Ollama 어댑터. 메일 내용이 밖으로 나가지 않는 로컬 LLM·임베딩 경로다.

- 주소는 loopback만(config.loopback_url), 프록시 환경 변수는 무시한다(trust_env=False).
- 연결 실패·시간 초과·5xx만 정해진 횟수 재시도한다. 형식 위반 재시도는 각 기능이 한다.
- 오류에는 고정 코드와 고정 안내만 담고, 메일 내용·응답 원문을 넣지 않는다.
"""

from collections.abc import Sequence

import httpx

from app.ai.config import EmbeddingSettings, OllamaSettings
from app.ai.interfaces import (
    EmbeddingRequest,
    GenerationRequest,
    ProviderCallError,
    ProviderIdentity,
    ProvidersNotConfigured,
)
from app.ai.json_output import clean_json_text

MESSAGES = {
    "ollama_unreachable": (
        "Ollama에 연결하지 못했어요. "
        "맥북에서 Ollama 앱 또는 'ollama serve'가 실행 중인지 확인하세요."
    ),
    "ollama_timeout": (
        "로컬 모델 응답이 제한 시간 안에 오지 않았어요. 더 작은 모델을 쓰거나 "
        "OLLAMA_TIMEOUT_SECONDS·EMBEDDING_TIMEOUT_SECONDS를 늘리세요."
    ),
    "ollama_model_not_found": (
        "Ollama에 모델이 없어요. 'ollama pull {model}'로 받은 뒤 다시 실행하세요."
    ),
    "ollama_bad_request": (
        "Ollama가 요청을 거부했어요. Ollama를 최신으로 올리거나 OLLAMA_FORMAT=json, "
        "OLLAMA_THINK를 비워서 다시 시도하세요."
    ),
    "ollama_error": "Ollama 호출에 실패했어요. 'ollama ps'와 Ollama 로그를 확인하세요.",
    "ollama_invalid_response": "Ollama 응답 형식을 읽지 못했어요. Ollama 버전을 확인하세요.",
}


def _error(code: str, model: str = "") -> ProviderCallError:
    return ProviderCallError(MESSAGES[code].format(model=model), code=code)


class _OllamaClient:
    def __init__(self, base_url: str, timeout: float, retries: int, transport=None):
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries
        self.transport = transport

    @property
    def call_timeout(self) -> float:
        # 바깥(기능 쪽) 시간 제한은 재시도까지 기다릴 수 있게 잡는다.
        return self.timeout * (self.retries + 1) + 5

    async def post(self, path: str, body: dict, model: str) -> dict:
        last = "ollama_error"
        for _attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    trust_env=False,
                    follow_redirects=False,
                    transport=self.transport,
                ) as client:
                    response = await client.post(path, json=body)
            except httpx.TimeoutException:
                last = "ollama_timeout"
                continue
            except httpx.TransportError:
                last = "ollama_unreachable"
                continue
            if response.status_code == 404:
                raise _error("ollama_model_not_found", model)
            if response.status_code >= 500:
                last = "ollama_error"
                continue
            if response.status_code != 200:
                raise _error("ollama_bad_request")
            try:
                payload = response.json()
            except ValueError:
                raise _error("ollama_invalid_response") from None
            if not isinstance(payload, dict):
                raise _error("ollama_invalid_response")
            return payload
        raise _error(last, model)


class OllamaGeneration:
    external_transfer = False

    def __init__(self, settings: OllamaSettings, *, transport=None):
        if settings.models is None:
            raise ProvidersNotConfigured("OLLAMA_MODEL을 설정하세요")
        self.settings = settings
        self.client = _OllamaClient(
            settings.base_url, settings.timeout_seconds, settings.retries, transport
        )
        self.identity = ProviderIdentity(
            provider="ollama", model=settings.models["analysis"], mode="live"
        )
        self.call_timeout = self.client.call_timeout

    def model_for(self, purpose: str) -> str:
        return self.settings.models[purpose]

    async def generate(self, request: GenerationRequest) -> str:
        model = self.model_for(request.purpose)
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0},
            "keep_alive": self.settings.keep_alive,
        }
        if self.settings.format_mode == "schema":
            body["format"] = request.response_schema
        elif self.settings.format_mode == "json":
            body["format"] = "json"
        if self.settings.think is not None:
            body["think"] = self.settings.think
        payload = await self.client.post("/api/chat", body, model)
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise _error("ollama_invalid_response")
        return clean_json_text(content)


class OllamaEmbedding:
    external_transfer = False

    def __init__(self, settings: EmbeddingSettings, base_url: str, *, transport=None):
        self.settings = settings
        self.dimensions = settings.dimensions
        self.client = _OllamaClient(base_url, settings.timeout_seconds, 1, transport)
        self.identity = ProviderIdentity(provider="ollama", model=settings.model, mode="live")
        self.call_timeout = self.client.call_timeout

    async def embed(self, request: EmbeddingRequest) -> Sequence[Sequence[float]]:
        # bge-m3는 문서·질문 구분 접두어가 필요 없다. 개수·차원 검사는 호출 쪽에서 한다.
        payload = await self.client.post(
            "/api/embed",
            {"model": self.settings.model, "input": list(request.texts), "truncate": True},
            self.settings.model,
        )
        vectors = payload.get("embeddings")
        if not isinstance(vectors, list):
            raise _error("ollama_invalid_response")
        return vectors
