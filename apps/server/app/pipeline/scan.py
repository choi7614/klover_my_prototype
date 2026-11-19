"""F1의 검증 가능한 분석 결과만 받는다. AI 제공자를 호출하지 않는다."""

from app.schemas.f5 import ScanInput
from app.services.f5_errors import F5Error


def scan(repository, owner, analysis: ScanInput):
    analysis = ScanInput.model_validate(analysis)
    candidates = [("calendar", row) for row in analysis.events]
    candidates += [("todo", row) for row in analysis.action_items]
    if analysis.reply is not None:
        candidates.append(("reply", analysis.reply))
    keys = {}
    for kind, candidate in candidates:
        key = (kind, candidate.action_key)
        if key in keys and keys[key] != candidate:
            raise F5Error("analysis_identity_conflict", 422)
        keys[key] = candidate
    return repository.ingest(owner, analysis, candidates)
