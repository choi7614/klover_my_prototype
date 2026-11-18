import asyncio
import json
from copy import deepcopy

import pytest

from app.pipeline.evaluate import evaluate_synthetic
from tests.f1.support import CASES, DATASET, ScriptedGeneration


def test_test_double_matches_never_become_actual_model_accuracy():
    evaluation = asyncio.run(evaluate_synthetic(DATASET, ScriptedGeneration()))
    assert evaluation.total == evaluation.valid == evaluation.category_matches == 23
    assert evaluation.deadline_matches == 23
    assert evaluation.provider.mode == "test"
    assert evaluation.actual_model_accuracy is None


def test_invalid_and_incorrect_responses_count_against_all_cases():
    first = {**CASES[0]["expected"], "category": "notice"}
    dataset = {**DATASET, "cases": CASES[:2]}
    provider = ScriptedGeneration([json.dumps(first), "{}", "{}"])
    evaluation = asyncio.run(evaluate_synthetic(dataset, provider))
    assert evaluation.total == 2 and evaluation.valid == 1 and evaluation.category_matches == 0
    assert evaluation.actual_model_accuracy is None


@pytest.mark.parametrize("mutation", ["not_synthetic", "duplicate", "gmail", "foreign_id"])
def test_unsafe_evaluation_data_is_rejected_before_calling_provider(mutation):
    dataset = deepcopy(DATASET)
    if mutation == "not_synthetic":
        dataset["synthetic"] = False
    elif mutation == "duplicate":
        dataset["cases"].append(dataset["cases"][0])
    elif mutation == "gmail":
        dataset["cases"][0]["mail"]["source"] = "gmail"
    else:
        dataset["cases"][0]["expected"]["mail_id"] = "foreign-id"
    provider = ScriptedGeneration()
    with pytest.raises(ValueError):
        asyncio.run(evaluate_synthetic(dataset, provider))
    assert provider.calls == []
