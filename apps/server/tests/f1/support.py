"""합성 정답을 반환하는 테스트 대역. 모델 정확도 평가에 사용하지 않는다."""

import json
from collections import deque
from pathlib import Path

from app.ai.interfaces import ProviderIdentity
from app.schemas.mail_analysis import AnalysisMail

ROOT = Path(__file__).resolve().parents[4]
DATASET = json.loads((ROOT / "fixtures/mails/F1-mail-analysis.json").read_text())
CASES = DATASET["cases"]


def sample_mail(index=0, **overrides):
    return AnalysisMail.model_validate({**CASES[index]["mail"], **overrides})


class ScriptedGeneration:
    identity = ProviderIdentity(provider="f1-test-double", model="scripted-json", mode="test")

    def __init__(self, responses=None):
        self.responses = deque(responses) if responses is not None else None
        self.calls = []

    async def generate(self, request):
        self.calls.append(request)
        if self.responses is None:
            mail_id = json.loads(request.user_prompt)["mail"]["mail_id"]
            return json.dumps(
                next(case["expected"] for case in CASES if case["mail"]["mail_id"] == mail_id),
                ensure_ascii=False,
            )
        response = self.responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


class ScriptedEmbedding:
    identity = ProviderIdentity(provider="f1-test-double", model="synthetic-vector", mode="test")
    dimensions = 3

    def __init__(self, response=None):
        self.calls = []
        self.response = response

    async def embed(self, request):
        self.calls.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        if self.response is not None:
            return self.response
        return [[0.1, 0.2, float(seq + 1)] for seq in range(len(request.texts))]
