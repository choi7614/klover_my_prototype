"""공통 AI 담당자가 연결할 F2 포트. 외부 제공자나 가짜 응답은 구현하지 않는다."""

from typing import Protocol

from app.schemas.profile_draft import GeneratedDraft, GenerationInput


class F2Error(Exception):
    def __init__(self, code: str, status: int, message: str):
        self.code, self.status, self.message = code, status, message
        super().__init__(code)


class DraftAI(Protocol):
    async def generate(self, request: GenerationInput) -> GeneratedDraft: ...


class RelatedMailSearch(Protocol):
    """F1이 같은 스레드·상대와 의미 유사 상위 3건을 합쳐 중복 없는 ID 최대 50개를 준다."""

    async def find_ids(self, *, user_id: str, account_id: str, mail_id: str) -> tuple[str, ...]: ...


class UnavailableDraftAI:
    async def generate(self, request: GenerationInput) -> GeneratedDraft:
        raise F2Error("ai_unavailable", 503, "AI 연결이 준비되지 않았어요. 직접 작성해 주세요.")
