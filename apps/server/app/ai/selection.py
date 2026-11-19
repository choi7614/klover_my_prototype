"""로컬 운영자용 기능별 AI 설정. 키·설정은 서버의 암호화 파일에만 저장한다."""

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.ai.config import ENV_FILE, environment_values
from app.ai.interfaces import GenerationRequest, ProviderIdentity, ProvidersNotConfigured
from app.ai.runtime import load_generation

Provider = Literal["ollama", "claude"]
Choice = Literal["default", "ollama", "claude"]


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    draft: Provider = "ollama"
    search: Provider = "ollama"
    weekly_report: Provider = "ollama"


class AIUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    defaults: Defaults
    external_consent: bool = Field(strict=True)
    api_key: SecretStr | None = Field(default=None, max_length=512)
    clear_key: bool = False
    claude_model: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:/-]{1,200}$")


class AIState(BaseModel):
    defaults: Defaults
    external_consent: bool
    claude_key_set: bool
    local_configured: bool
    claude_model: str


class AISelectionError(ProvidersNotConfigured):
    pass


class AISettingsStore:
    def __init__(self, directory: Path | None = None, *, values=None):
        self.directory = directory or ENV_FILE.parent / ".local-secrets"
        self.values = environment_values if values is None else lambda: dict(values)
        self.lock = threading.RLock()

    def _cipher(self, *, create=False):
        target = self.directory / "ai-settings.key"
        if not create:
            return Fernet(target.read_bytes())
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
        return Fernet(target.read_bytes())

    def read(self):
        with self.lock:
            target = self.directory / "ai-settings.enc"
            if not target.exists():
                # 최초에는 기존 운영 설정을 이어받는다. 외부 전송 동의는 별도로 받는다.
                provider = self.values().get("AI_PROVIDER", "ollama")
                provider = provider if provider in {"claude", "ollama"} else "ollama"
                return {
                    "defaults": Defaults(
                        **dict.fromkeys(Defaults.model_fields, provider)
                    ).model_dump(),
                    "external_consent": False,
                    "api_key": None,
                }
            try:
                return json.loads(self._cipher().decrypt(target.read_bytes()))
            except Exception:
                raise AISelectionError(
                    "AI 설정 파일을 읽지 못했어요. 기존 파일을 보존하고 설정을 확인하세요."
                ) from None

    def state(self):
        data = self.read()
        values = self.values()
        return AIState(
            defaults=data["defaults"],
            external_consent=data["external_consent"],
            claude_key_set=bool(data.get("api_key") or values.get("ANTHROPIC_API_KEY")),
            local_configured=bool(values.get("OLLAMA_MODEL")),
            claude_model=data.get("claude_model")
            or values.get("CLAUDE_MODEL")
            or "claude-opus-5-5",
        )

    def update(self, update: AIUpdate):
        with self.lock:
            data = self.read()
            key = update.api_key.get_secret_value().strip() if update.api_key is not None else None
            if key is not None and (not key or any(c.isspace() for c in key)):
                raise AISelectionError("Claude API 키 형식을 확인하세요.")
            if update.clear_key and key is not None:
                raise AISelectionError("키 저장과 삭제는 따로 요청하세요.")
            data.update(
                defaults=update.defaults.model_dump(), external_consent=update.external_consent
            )
            if update.claude_model is not None:
                data["claude_model"] = update.claude_model
            if key is not None or update.clear_key:
                data["api_key"] = key
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            encrypted = self._cipher(create=True).encrypt(json.dumps(data).encode())
            fd, temporary = tempfile.mkstemp(prefix="ai-settings-", dir=self.directory)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(encrypted)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.directory / "ai-settings.enc")
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return self.state()


# 요청별 스냅샷: 검색 해석/답변 중 설정이 바뀌거나 동시 요청이 와도 섞이지 않는다.
_selection: ContextVar[tuple | None] = ContextVar("ai_selection", default=None)


@contextmanager
def selected(store, choice: Choice | None = None):
    token = _selection.set((store.read(), choice, store.values()))
    try:
        yield
    finally:
        _selection.reset(token)


class SelectedGeneration:
    identity = ProviderIdentity(provider="selected", model="per-request", mode="live")
    external_transfer = True  # 자동 분석에는 주입하지 않는다.

    def __init__(self, store, *, loader=load_generation):
        self.store, self.loader = store, loader

    def provider_for(self, purpose):
        data, choice, _values = _selection.get() or (self.store.read(), None, self.store.values())
        return choice if choice not in {None, "default"} else data["defaults"][purpose]

    async def generate(self, request: GenerationRequest):
        if request.purpose not in Defaults.model_fields:
            raise AISelectionError("자동 분석에는 로컬 AI만 사용할 수 있어요.")
        data, _choice, values = _selection.get() or (self.store.read(), None, self.store.values())
        provider = self.provider_for(request.purpose)
        values = {**values, "AI_PROVIDER": provider}
        if provider == "claude":
            if not data["external_consent"]:
                raise AISelectionError(
                    "AI 설정에서 외부 전송과 API 비용 안내를 확인하고 Claude 사용을 허용하세요."
                )
            values["AI_CLAUDE_EXTERNAL_CONSENT"] = "true"
            if data.get("claude_model"):
                values["CLAUDE_MODEL"] = data["claude_model"]
                for purpose in Defaults.model_fields:
                    values[f"CLAUDE_MODEL_{purpose.upper()}"] = data["claude_model"]
            if data.get("api_key"):
                values["ANTHROPIC_API_KEY"] = data["api_key"]
        generator = self.loader(values)
        try:
            return await generator.generate(request)
        finally:
            if provider == "claude" and hasattr(getattr(generator, "client", None), "close"):
                await generator.client.close()
