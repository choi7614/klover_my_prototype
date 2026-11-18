"""Google과 통신하는 경계. 첫 단위는 토큰 교환과 Gmail 계정 정보만 조회한다."""

import hashlib
import json
import secrets
import threading
import time
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.google_config import GMAIL_SCOPE, REDIRECT_URI, GoogleConnectionError, GoogleSettings


@dataclass(repr=False)
class PendingLogin:
    browser_hash: str
    verifier: str
    expires: float


class LoginAttempts:
    """프로세스 한 개에서만 쓰는 10분·일회용 로그인 상태. 재시작 후 다시 시작한다."""

    def __init__(self):
        self._attempts: dict[str, PendingLogin] = {}
        self._lock = threading.Lock()

    def begin(self, browser: str) -> tuple[str, str]:
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        now = time.monotonic()
        with self._lock:
            self._attempts = {k: v for k, v in self._attempts.items() if v.expires > now}
            if len(self._attempts) >= 128:
                raise GoogleConnectionError("로그인 요청이 많습니다. 잠시 후 다시 시작하세요")
            self._attempts[_hash(state)] = PendingLogin(_hash(browser), verifier, now + 600)
        return state, verifier

    def consume(self, state: str, browser: str) -> str:
        with self._lock:
            attempt = self._attempts.get(_hash(state))
            if (
                attempt is None
                or attempt.expires <= time.monotonic()
                or not secrets.compare_digest(attempt.browser_hash, _hash(browser))
            ):
                raise GoogleConnectionError("로그인 요청이 만료됐습니다. 처음부터 다시 연결하세요")
            del self._attempts[_hash(state)]
            return attempt.verifier


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def authorization_url(settings: GoogleSettings, state: str, verifier: str) -> str:
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": GMAIL_SCOPE,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent select_account",
            "login_hint": settings.expected_email,
        }
    )


class GoogleOAuthClient:
    def __init__(self, settings: GoogleSettings, transport=None):
        self.settings = settings
        self.transport = transport

    def exchange(self, code: str, verifier: str) -> tuple[str, dict]:
        try:
            with httpx.Client(
                timeout=15,
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                response = client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.settings.client_id,
                        "client_secret": self.settings.client_secret,
                        "code": code,
                        "code_verifier": verifier,
                        "redirect_uri": REDIRECT_URI,
                        "grant_type": "authorization_code",
                    },
                )
                response.raise_for_status()
                tokens = response.json()
                access = tokens["access_token"]
                if not isinstance(access, str) or not access or len(access) > 16384:
                    raise ValueError
                if tokens.get("token_type", "").lower() != "bearer":
                    raise ValueError
                if set(tokens.get("scope", "").split()) != {GMAIL_SCOPE}:
                    raise ValueError
                expires = tokens["expires_in"]
                if type(expires) is not int or not 0 < expires <= 86400:
                    raise ValueError
                profile = client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": "Bearer " + access},
                )
                profile.raise_for_status()
                email = profile.json()["emailAddress"]
                if (
                    not isinstance(email, str)
                    or email.strip().lower() != self.settings.expected_email
                ):
                    raise ValueError
                refresh = tokens.get("refresh_token")
                if refresh is not None and (
                    not isinstance(refresh, str) or not refresh or len(refresh) > 16384
                ):
                    raise ValueError
                # 외부 응답의 불필요한 필드(ID 토큰 등)는 저장하지 않는다.
                safe_tokens = {
                    "access_token": access,
                    "refresh_token": refresh,
                    "scope": GMAIL_SCOPE,
                    "expires_in": expires,
                }
                json.dumps(safe_tokens)
                return email.strip().lower(), safe_tokens
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
            raise GoogleConnectionError(
                "Google 연결을 확인하지 못했습니다. 권한과 선택한 테스트 계정을 확인하세요"
            ) from None
