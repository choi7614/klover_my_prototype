"""F2 출력 거절의 고정 사유. 본문·키·모델 원문·예외 상세를 기록하지 않는다."""

import logging
from enum import StrEnum

from pydantic import ValidationError

from app.ai.f2_port import F2Error

logger = logging.getLogger(__name__)


class OutputReason(StrEnum):
    JSON_INVALID = "json_invalid"
    SCHEMA_INVALID = "schema_invalid"
    BODY_OR_DIRECTIONS = "body_or_directions_invalid"
    SOURCE = "source_not_allowed"
    LEARNED_PHRASE = "learned_phrase_mismatch"
    OVERLAP = "evidence_overlap"
    SPAN = "evidence_span_invalid"
    DIRECTION = "direction_mismatch"
    EXCLUDED_PHRASE = "excluded_phrase"
    INCOMING_ECHO = "incoming_echo"
    EDIT_CODE = "edit_code_as_direction"
    VALIDATION = "validation_failed"


# 공개 안내와 보정 요청 모두 코드에서 정한 문장만 사용한다.
REASONS = {
    OutputReason.JSON_INVALID: ("응답 JSON 형식", "JSON 객체 하나만 반환하세요."),
    OutputReason.SCHEMA_INVALID: (
        "응답 항목·자료형",
        "body, directions, selected_direction 항목과 자료형만 지키세요. 근거는 반환하지 마세요.",
    ),
    OutputReason.BODY_OR_DIRECTIONS: (
        "빈 본문 또는 답장 방향 구성",
        "본문은 비우지 말고 방향 2~3개를 중복 없이 반환하세요. 선택 방향을 목록에 포함하세요.",
    ),
    OutputReason.SOURCE: (
        "허용되지 않은 근거 출처",
        "근거는 서버가 계산합니다. evidence를 반환하지 마세요.",
    ),
    OutputReason.LEARNED_PHRASE: (
        "학습 표현과 근거의 불일치",
        "학습 표현은 learned_phrases 항목을 그대로 사용하세요.",
    ),
    OutputReason.OVERLAP: (
        "본문에서 겹치는 근거 위치",
        "근거는 서버가 계산합니다. evidence를 반환하지 마세요.",
    ),
    OutputReason.SPAN: ("근거 위치 범위", "근거는 서버가 계산합니다. evidence를 반환하지 마세요."),
    OutputReason.DIRECTION: (
        "요청한 답장 방향과의 불일치",
        "요청 direction을 selected_direction과 directions에 그대로 포함하세요.",
    ),
    OutputReason.EXCLUDED_PHRASE: ("사용자가 제외한 표현 포함", "excluded_phrases를 쓰지 마세요."),
    OutputReason.INCOMING_ECHO: (
        "답장 대신 수신 원문 반환",
        "수신 원문을 반복하지 말고 Klover 사용자가 원문 발신자에게 답하는 메일을 쓰세요.",
    ),
    OutputReason.EDIT_CODE: (
        "답장 방향에 수정 명령 포함",
        "shorter/politer/rewrite는 action이며 답장 방향이 아닙니다. 한국어 내용 방향을 반환하세요.",
    ),
    OutputReason.VALIDATION: ("본문·근거 검증", "본문·근거·방향의 출력 계약을 지키세요."),
}


class InvalidDraftOutput(F2Error):
    def __init__(self, reason: OutputReason = OutputReason.VALIDATION):
        self.reason = reason
        super().__init__(
            "invalid_ai_output",
            502,
            f"AI 결과의 본문과 근거를 확인하지 못했어요. ({REASONS[reason][0]})",
        )


def schema_reason(error: ValidationError) -> OutputReason:
    # 입력값·사용자 JSON의 필드명·검증 예외 메시지까지 로그에 넣지 않는다.
    failures = error.errors(include_input=False, include_context=False, include_url=False)
    if any(item["type"] == "json_invalid" for item in failures):
        return OutputReason.JSON_INVALID
    if any(item["type"] == "value_error" and not item["loc"] for item in failures):
        return OutputReason.BODY_OR_DIRECTIONS
    return OutputReason.SCHEMA_INVALID


def record_rejection(reason: OutputReason, *, attempt: int, operation: str):
    operation = operation if operation in {"create", "revise", "preview"} else "unknown"
    logger.warning(
        "F2 output rejected reason=%s attempt=%d operation=%s", reason.value, attempt, operation
    )


def repair_hint(reason: OutputReason) -> str:
    return f"검증 사유: {reason.value}. {REASONS[reason][1]} 잘못된 근거를 생략해 숨기지 마세요."


PROVIDER_REASONS = {
    "provider_not_configured": "AI 설정 미완료",
    "provider_failed": "AI 제공자 오류",
    "ollama_unreachable": "로컬 AI 연결 실패",
    "ollama_timeout": "로컬 AI 응답 시간 초과",
    "ollama_model_not_found": "로컬 모델 없음",
    "ollama_bad_request": "로컬 AI 요청 설정",
    "ollama_error": "로컬 AI 서비스 오류",
    "ollama_invalid_response": "로컬 AI 응답 형식",
    "claude_timeout": "Claude 응답 시간 초과",
    "both_providers_failed": "Claude와 로컬 AI 모두 실패",
}


def record_provider_failure(code: str, *, operation: str) -> str:
    safe_reason = code if code in PROVIDER_REASONS else "provider_failed"
    operation = operation if operation in {"create", "revise", "preview"} else "unknown"
    logger.warning("F2 provider failed reason=%s operation=%s", safe_reason, operation)
    return PROVIDER_REASONS[safe_reason]
