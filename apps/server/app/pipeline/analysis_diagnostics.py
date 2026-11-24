"""F1의 고정 실패 사유와 보정 지시. 사용자/메일 식별자·입력·AI 원문은 기록하지 않는다."""

import logging
from enum import StrEnum

from pydantic import ValidationError

from app.ai.interfaces import ProviderCallError

logger = logging.getLogger(__name__)


class Reason(StrEnum):
    JSON = "json_invalid"
    MISSING = "schema_missing"
    EXTRA = "schema_extra"
    SCHEMA = "schema_invalid"
    SIZE = "response_size_or_type"
    SUMMARY = "summary_invalid"
    CATEGORY = "category_invalid"
    ACTIONS = "actions_invalid"
    EVENTS = "events_invalid"
    EVIDENCE = "evidence_invalid"
    MAIL_ID = "mail_id_mismatch"
    SOURCE = "source_invalid"
    INPUT_SIZE = "input_too_large"
    TIMEOUT = "timeout"
    PROVIDER = "provider_failed"
    OLLAMA_TIMEOUT = "ollama_timeout"
    OLLAMA_UNREACHABLE = "ollama_unreachable"
    OLLAMA_MODEL = "ollama_model_not_found"
    OLLAMA_REQUEST = "ollama_bad_request"
    OLLAMA_ERROR = "ollama_error"
    OLLAMA_RESPONSE = "ollama_invalid_response"


HINTS = {
    Reason.JSON: "마크다운이나 설명 없이 JSON 객체 하나만 반환하세요.",
    Reason.MISSING: "스키마의 필수 항목을 빠짐없이 반환하세요. 없는 요청·일정은 빈 배열입니다.",
    Reason.EXTRA: "스키마에 없는 필드나 설명을 추가하지 마세요.",
    Reason.SCHEMA: "스키마의 자료형을 지키세요. needs_reply는 문자열이 아닌 true/false입니다.",
    Reason.SIZE: "정해진 길이 안의 JSON 객체 하나만 반환하세요.",
    Reason.SUMMARY: "summary는 비어 있지 않은 한국어 1~2줄, 1000자 이내입니다.",
    Reason.CATEGORY: (
        "category는 work_request/meeting/approval/report_share/notice/external/newsletter "
        "중 하나이며 한국어 이름을 쓰지 마세요."
    ),
    Reason.ACTIONS: (
        "action_items는 text와 due를 가진 객체 배열입니다. due는 유효한 YYYY-MM-DD 또는 null이며 "
        "실제 요청과 확인 가능한 날짜만 추출하세요."
    ),
    Reason.EVENTS: (
        "events의 start/end에는 시간대 오프셋을 포함하세요. end가 있으면 start보다 늦어야 합니다. "
        "일시를 알 수 없는 일정은 추측하지 마세요."
    ),
    Reason.EVIDENCE: (
        "evidence_spans는 body_text의 Python 문자 위치입니다. 정수 0 <= start < end <= "
        "body_text_length를 지키고 실제 원문 근거 위치를 다시 확인하세요."
    ),
    Reason.MAIL_ID: "mail_id는 입력 mail.mail_id와 글자 그대로 같아야 합니다.",
    Reason.SOURCE: "입력 메일 ID와 원문 안의 근거 위치를 다시 확인하세요.",
}


def schema_reason(error: ValidationError) -> Reason:
    # 오류 메시지·입력·동적 JSON 필드명을 출력하거나 보정 지시에 복사하지 않는다.
    failures = error.errors(include_input=False, include_context=False, include_url=False)
    for error_type, reason in (
        ("json_invalid", Reason.JSON),
        ("missing", Reason.MISSING),
        ("extra_forbidden", Reason.EXTRA),
    ):
        if any(item["type"] == error_type for item in failures):
            return reason
    for field, reason in (
        ("summary", Reason.SUMMARY),
        ("category", Reason.CATEGORY),
        ("action_items", Reason.ACTIONS),
        ("events", Reason.EVENTS),
        ("evidence_spans", Reason.EVIDENCE),
    ):
        if any(item["loc"] and item["loc"][0] == field for item in failures):
            return reason
    return Reason.SCHEMA


def provider_reason(error: Exception) -> Reason:
    if isinstance(error, TimeoutError):
        return Reason.TIMEOUT
    if isinstance(error, ProviderCallError):
        # 제공자 메시지·모델명은 로그에 넣지 않는다. 허용한 코드만 남긴다.
        for reason in (
            Reason.OLLAMA_TIMEOUT,
            Reason.OLLAMA_UNREACHABLE,
            Reason.OLLAMA_MODEL,
            Reason.OLLAMA_REQUEST,
            Reason.OLLAMA_ERROR,
            Reason.OLLAMA_RESPONSE,
        ):
            if error.code == reason.value:
                return reason
    return Reason.PROVIDER


def record_failure(reason: Reason, attempt: int) -> None:
    logger.warning("F1 analysis rejected reason=%s attempt=%d", reason.value, attempt)


def repair_hint(reason: Reason) -> str:
    return (
        f"검증 사유: {reason.value}. {HINTS[reason]} "
        "잘못된 결과를 숨기려고 실제 요청·근거를 생략하지 마세요. 전체 객체를 다시 작성하세요."
    )
