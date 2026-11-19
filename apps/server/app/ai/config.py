"""AI 제공자 설정. .env와 환경 변수를 필요할 때만 읽고 키를 출력하지 않는다."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import dotenv_values

from app.ai.interfaces import ProvidersNotConfigured

Purpose = Literal["analysis", "draft", "search", "weekly_report", "scan"]
PURPOSES: tuple[Purpose, ...] = ("analysis", "draft", "search", "weekly_report", "scan")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,200}$")
ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class AIConfigurationError(ProvidersNotConfigured):
    """설정 오류도 '미연결'로 다룬다. 메시지에는 키·주소 외 값을 넣지 않는다."""


@dataclass(frozen=True)
class ClaudeSettings:
    api_key: str = field(repr=False)
    models: Mapping[Purpose, str]
    effort: str
    timeout_seconds: float
    max_retries: int
    max_tokens: int


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str
    models: Mapping[Purpose, str] | None
    timeout_seconds: float
    retries: int
    format_mode: Literal["schema", "json", "none"]
    think: bool | None
    keep_alive: str


@dataclass(frozen=True)
class EmbeddingSettings:
    model: str
    dimensions: int
    timeout_seconds: float


@dataclass(frozen=True)
class AISettings:
    provider: Literal["claude", "ollama"] | None
    claude: ClaudeSettings | None = None
    ollama: OllamaSettings | None = None
    embedding: EmbeddingSettings | None = None


def environment_values() -> dict[str, str | None]:
    return {**dotenv_values(ENV_FILE), **os.environ}


def _text(values, key, default=None):
    value = values.get(key)
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def _number(values, key, default, low, high, kind=float):
    raw = _text(values, key)
    if raw is None:
        return default
    try:
        number = kind(raw)
    except ValueError:
        raise AIConfigurationError(f"{key}는 {low}~{high} 숫자여야 합니다") from None
    if not low <= number <= high:
        raise AIConfigurationError(f"{key}는 {low}~{high} 숫자여야 합니다")
    return number


def _model(values, key, default=None):
    name = _text(values, key, default)
    if name is not None and not MODEL_NAME.fullmatch(name):
        raise AIConfigurationError(f"{key}의 모델 이름 형식을 확인하세요")
    return name


def _models(values, prefix, default):
    """기능별 모델(예: CLAUDE_MODEL_ANALYSIS)이 없으면 공통 모델을 쓴다."""
    return {purpose: _model(values, f"{prefix}_{purpose.upper()}", default) for purpose in PURPOSES}


def loopback_url(raw: str) -> str:
    """Ollama 주소는 이 컴퓨터(loopback)의 http만 허용한다. 메일이 외부로 나가지 않게 한다."""
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError:
        raise AIConfigurationError("OLLAMA_BASE_URL 형식을 확인하세요") from None
    if (
        parts.scheme != "http"
        or parts.hostname not in LOOPBACK_HOSTS
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise AIConfigurationError(
            "OLLAMA_BASE_URL은 이 컴퓨터 주소(http://localhost:11434 등)만 허용합니다"
        )
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    return f"http://{host}:{port or 11434}"


def _claude(values) -> ClaudeSettings:
    if _text(values, "AI_CLAUDE_TEST_DATA_ONLY", "").lower() != "true":
        raise AIConfigurationError(
            "Claude는 메일을 외부로 보냅니다. 테스트 데이터만 쓴다는 확인으로 "
            "AI_CLAUDE_TEST_DATA_ONLY=true를 설정하세요"
        )
    api_key = _text(values, "ANTHROPIC_API_KEY")
    if api_key is None:
        raise AIConfigurationError("ANTHROPIC_API_KEY를 설정하세요")
    effort = _text(values, "CLAUDE_EFFORT", "low").lower()
    if effort not in EFFORTS:
        raise AIConfigurationError("CLAUDE_EFFORT는 low/medium/high/xhigh/max 중 하나입니다")
    return ClaudeSettings(
        api_key=api_key,
        models=_models(values, "CLAUDE_MODEL", _model(values, "CLAUDE_MODEL", "claude-opus-5-5")),
        effort=effort,
        timeout_seconds=_number(values, "CLAUDE_TIMEOUT_SECONDS", 120.0, 5, 600),
        max_retries=_number(values, "CLAUDE_MAX_RETRIES", 2, 0, 5, int),
        max_tokens=_number(values, "CLAUDE_MAX_TOKENS", 16000, 1024, 64000, int),
    )


def _ollama(values, *, needs_model: bool) -> OllamaSettings:
    default_model = _model(values, "OLLAMA_MODEL")
    if needs_model and default_model is None:
        raise AIConfigurationError(
            "OLLAMA_MODEL을 설정하세요 (ollama list에 보이는 이름, 예: qwen3:14b)"
        )
    format_mode = _text(values, "OLLAMA_FORMAT", "schema").lower()
    if format_mode not in {"schema", "json", "none"}:
        raise AIConfigurationError("OLLAMA_FORMAT은 schema/json/none 중 하나입니다")
    think_raw = _text(values, "OLLAMA_THINK", "").lower()
    if think_raw not in {"", "true", "false"}:
        raise AIConfigurationError("OLLAMA_THINK는 true/false 또는 빈 값입니다")
    keep_alive = _text(values, "OLLAMA_KEEP_ALIVE", "10m")
    if not re.fullmatch(r"-?\d{1,6}[smh]?", keep_alive):
        raise AIConfigurationError("OLLAMA_KEEP_ALIVE 형식을 확인하세요 (예: 10m)")
    return OllamaSettings(
        base_url=loopback_url(_text(values, "OLLAMA_BASE_URL", "http://localhost:11434")),
        models=_models(values, "OLLAMA_MODEL", default_model) if default_model else None,
        timeout_seconds=_number(values, "OLLAMA_TIMEOUT_SECONDS", 120.0, 5, 1800),
        retries=_number(values, "OLLAMA_RETRIES", 1, 0, 3, int),
        format_mode=format_mode,
        think=None if think_raw == "" else think_raw == "true",
        keep_alive=keep_alive,
    )


def read_ai_settings(values: Mapping[str, str | None] | None = None) -> AISettings:
    values = environment_values() if values is None else values
    provider = _text(values, "AI_PROVIDER", "").lower()
    if provider == "":
        return AISettings(provider=None)
    if provider not in {"claude", "ollama"}:
        raise AIConfigurationError("AI_PROVIDER는 claude 또는 ollama입니다")
    # 임베딩은 어떤 제공자를 고르든 이 컴퓨터의 Ollama에서 만든다(Claude는 임베딩 없음).
    embedding = EmbeddingSettings(
        model=_model(values, "EMBEDDING_MODEL", "bge-m3"),
        dimensions=_number(values, "EMBEDDING_DIMENSIONS", 1024, 1, 4096, int),
        timeout_seconds=_number(values, "EMBEDDING_TIMEOUT_SECONDS", 60.0, 5, 600),
    )
    if provider == "claude":
        return AISettings(
            provider="claude",
            claude=_claude(values),
            ollama=_ollama(values, needs_model=False),
            embedding=embedding,
        )
    return AISettings(
        provider="ollama", ollama=_ollama(values, needs_model=True), embedding=embedding
    )
