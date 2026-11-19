"""읽기 전용 Gmail 통신. 외부 오류·응답 본문·토큰은 로그나 예외에 담지 않는다."""

import json
import re
from datetime import UTC, datetime, timedelta

import httpx

from app.google_config import GMAIL_SCOPE, GoogleConnectionError

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailStatusError(GoogleConnectionError):
    def __init__(self, status):
        super().__init__(
            f"Gmail 요청이 HTTP {status}로 거절됐습니다. 권한과 연결 상태를 확인하세요"
        )
        self.status = status


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise GoogleConnectionError("Gmail 응답 형식을 확인하지 못했습니다")
    return value


class GmailMailClient:
    def __init__(self, settings, transport=None):
        self.settings, self.transport = settings, transport
        self._client = None

    def __enter__(self):
        self._client = httpx.Client(
            timeout=15, trust_env=False, follow_redirects=False, transport=self.transport
        )
        return self

    def __exit__(self, *_):
        self._client.close()

    def get(self, path, access, params=None):
        try:
            with self._client.stream(
                "GET", BASE + path, headers={"Authorization": "Bearer " + access}, params=params
            ) as response:
                if response.status_code != 200:
                    raise GmailStatusError(response.status_code)
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 8 * 1024 * 1024:
                        raise GoogleConnectionError("메일 응답이 개발용 크기 제한을 초과했습니다")
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError
                return result
        except (httpx.HTTPError, ValueError, TypeError) as error:
            if isinstance(error, GoogleConnectionError):
                raise
            raise GoogleConnectionError(
                "Gmail 응답을 읽지 못했습니다. 연결 상태를 확인하세요"
            ) from None

    def profile(self, access):
        profile = self.get("/profile", access, {"fields": "emailAddress,historyId"})
        email, history = profile.get("emailAddress"), profile.get("historyId")
        if (
            not isinstance(email, str)
            or email.strip().lower() != self.settings.expected_email
            or not isinstance(history, str)
            or not re.fullmatch(r"[0-9]{1,128}", history)
        ):
            raise GoogleConnectionError("연결된 Gmail 계정 정보를 확인하지 못했습니다")
        return history

    def refresh(self, previous):
        try:
            response = self._client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.client_id,
                    "client_secret": self.settings.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": previous["refresh_token"],
                },
            )
            if response.status_code != 200 or len(response.content) > 65536:
                raise ValueError
            payload = response.json()
            access, expires = payload["access_token"], payload["expires_in"]
            scope = payload.get("scope", previous["scope"])
            refresh = payload.get("refresh_token", previous["refresh_token"])
            if (
                not all(isinstance(x, str) and 1 <= len(x) <= 16384 for x in [access, refresh])
                or type(expires) is not int
                or not 0 < expires <= 86400
                or not isinstance(scope, str)
                or set(scope.split()) != {GMAIL_SCOPE}
                or payload.get("token_type", "").lower() != "bearer"
            ):
                raise ValueError
            return {
                "access_token": access,
                "refresh_token": refresh,
                "scope": GMAIL_SCOPE,
                "expires_at": (datetime.now(UTC) + timedelta(seconds=expires)).isoformat(),
            }
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            raise GoogleConnectionError(
                "토큰을 갱신하지 못했습니다. Google 연결 동의를 다시 확인하세요"
            ) from None
