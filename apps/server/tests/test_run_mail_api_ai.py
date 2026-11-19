"""서버 실행 명령이 F2 답장 초안에 공통 AI를 연결하는지 확인한다. 실제 제공자는 부르지 않는다."""

import pytest

from app.ai.f2_port import UnavailableDraftAI
from app.ai.f2_shared_adapter import SharedDraftAI
from app.ai.interfaces import ProviderIdentity, ProvidersNotConfigured
from app.cli import run_mail_api


class Generator:
    def __init__(self, mode):
        self.identity = ProviderIdentity(provider="unit-test", model="synthetic", mode=mode)

    async def generate(self, request):  # pragma: no cover - 호출하지 않는다
        raise AssertionError("실행 명령 조립 중에는 생성하지 않는다")


def providers(mode):
    return lambda: (Generator(mode), object())


def test_draft_ai_is_unavailable_without_provider(monkeypatch):
    def missing():
        raise ProvidersNotConfigured("미설정")

    monkeypatch.setattr(run_mail_api, "load_providers", missing)
    assert isinstance(run_mail_api.draft_ai(), UnavailableDraftAI)


def test_draft_ai_rejects_non_live_provider(monkeypatch):
    monkeypatch.setattr(run_mail_api, "load_providers", providers("test"))
    assert isinstance(run_mail_api.draft_ai(), UnavailableDraftAI)


def test_draft_ai_uses_live_shared_provider(monkeypatch):
    monkeypatch.setattr(run_mail_api, "load_providers", providers("live"))
    adapter = run_mail_api.draft_ai()
    assert isinstance(adapter, SharedDraftAI)


@pytest.mark.parametrize("name", ["draft_ai", "search_ai"])
def test_ai_builders_do_not_raise_when_unconfigured(monkeypatch, name):
    def missing():
        raise ProvidersNotConfigured("미설정")

    monkeypatch.setattr(run_mail_api, "load_providers", missing)
    getattr(run_mail_api, name)()
