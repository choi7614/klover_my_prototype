"""합성 정답 데이터용 평가 경계. 테스트 대역의 일치율을 모델 정확도로 표시하지 않는다."""

import json
from dataclasses import dataclass
from time import perf_counter

from app.ai.interfaces import ProviderIdentity, TextGeneration
from app.pipeline.analyze import AnalysisFailed, analyze
from app.schemas.mail_analysis import AnalysisMail, AnalysisResult


@dataclass(frozen=True)
class Evaluation:
    provider: ProviderIdentity
    total: int
    valid: int
    category_matches: int
    deadline_matches: int
    elapsed_seconds: float

    @property
    def actual_model_accuracy(self) -> float | None:
        if self.provider.mode != "live" or self.total == 0:
            return None
        return self.category_matches / self.total


async def evaluate_synthetic(dataset: dict, provider: TextGeneration) -> Evaluation:
    if dataset.get("synthetic") is not True or not dataset.get("cases"):
        raise ValueError("명시된 합성 평가 데이터만 허용합니다")
    cases = []
    seen = set()
    for case in dataset["cases"]:
        mail = AnalysisMail.model_validate(case["mail"])
        expected = AnalysisResult.model_validate_json(json.dumps(case["expected"]))
        expected.check_source(mail)
        if (
            mail.source != "fixture"
            or mail.mail_id in seen
            or not mail.from_addr.endswith(".invalid")
        ):
            raise ValueError("중복 없는 합성 fixture 메일만 허용합니다")
        seen.add(mail.mail_id)
        cases.append((mail, expected))
    valid = category_matches = deadline_matches = 0
    started = perf_counter()
    for mail, expected in cases:
        try:
            actual, _ = await analyze(mail, provider)
        except AnalysisFailed:
            continue
        valid += 1
        category_matches += actual.category == expected.category
        deadline_matches += tuple(item.due for item in actual.action_items) == tuple(
            item.due for item in expected.action_items
        )
    return Evaluation(
        provider.identity,
        len(cases),
        valid,
        category_matches,
        deadline_matches,
        perf_counter() - started,
    )
