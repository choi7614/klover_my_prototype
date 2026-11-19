"""짧게 환산한 시계로 대기·취소·편집본 보존을 검사한다. 실제 AI·DB는 사용하지 않는다."""

import asyncio
from types import SimpleNamespace

import pytest
from test_f2_shared_adapter import input_for

from app.ai.f2_port import F2Error
from app.schemas.profile_draft import (
    ContextStatus,
    DraftCreate,
    DraftRevise,
    DraftState,
    GeneratedDraft,
    ProfileState,
    StyleState,
)
from app.services import profile_draft


class Repository:
    def __init__(self):
        self.saved = []
        self.previous = DraftState(
            draft_id="draft-old",
            mail_id="synthetic-only",
            directions=("확인", "문의"),
            selected_direction="확인",
            body="사용자가 편집한 본문",
            evidence=(),
            references=(),
            version=1,
            profile_version=1,
            context_status=ContextStatus(),
        )

    def profile(self, **_):
        return ProfileState(profile=input_for().profile, exists=True, version=1)

    def style(self, **_):
        return StyleState()

    def draft(self, **_):
        return self.previous

    def save_draft(self, **kwargs):
        self.saved.append(kwargs["draft"])
        return kwargs["draft"]


def service(ai):
    repository = Repository()
    reader = SimpleNamespace(detail=lambda _: input_for().original)
    return profile_draft.F2Service(
        repository=repository,
        mail_reader=reader,
        owner=SimpleNamespace(user_id="synthetic-user"),
        ai=ai,
    ), repository


@pytest.fixture
def scaled_timeout(monkeypatch):
    # 검사상의 1초를 실제 1밀리초로 환산해 장시간 기다리지 않는다.
    real_timeout = asyncio.timeout
    monkeypatch.setattr(
        profile_draft.asyncio, "timeout", lambda seconds: real_timeout(seconds / 1000)
    )


class DelayedAI:
    def __init__(self, simulated_seconds):
        self.simulated_seconds = simulated_seconds

    async def generate(self, _):
        await asyncio.sleep(self.simulated_seconds / 1000)
        return GeneratedDraft(
            body="요청을 확인했습니다.", directions=("확인", "문의"), selected_direction="확인"
        )


def test_generation_beyond_old_eight_seconds_is_saved(scaled_timeout):
    api, repository = service(DelayedAI(20))
    result = asyncio.run(api.create(DraftCreate(mail_id="synthetic-only")))
    assert result.body == "요청을 확인했습니다."
    assert repository.saved == [result]


def test_preview_beyond_old_two_seconds_completes(scaled_timeout):
    api, repository = service(DelayedAI(5))
    assert asyncio.run(api.preview(input_for().profile)).body == "요청을 확인했습니다."
    assert repository.saved == []


@pytest.mark.parametrize("operation", ["create", "revise"])
def test_deadline_cancels_generation_without_saving_or_replacing_edit(monkeypatch, operation):
    cancelled = []

    class BlockedAI:
        async def generate(self, _):
            try:
                await asyncio.Future()
            finally:
                cancelled.append(True)

    monkeypatch.setattr(profile_draft, "AI_TIMEOUT_SECONDS", 0.001)
    api, repository = service(BlockedAI())
    request = (
        api.create(DraftCreate(mail_id="synthetic-only"))
        if operation == "create"
        else api.revise(
            "draft-old", DraftRevise(action="rewrite", body="새 편집", expected_version=1)
        )
    )
    with pytest.raises(F2Error) as error:
        asyncio.run(request)
    assert error.value.code == "ai_timeout" and error.value.status == 504
    assert cancelled == [True]
    assert repository.saved == []
    assert repository.previous.body == "사용자가 편집한 본문"
