"""모델 응답에서 JSON 본문만 꺼내고, 제공자별 형식 강제용 스키마를 만든다.

검증은 각 기능의 출력 모델이 한다. 여기서는 내용을 고치거나 추측해 채우지 않는다.
"""

import copy
import re

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
FENCE = re.compile(r"^```(?:json)?\s*\n(.*?)\n?```$", re.DOTALL | re.IGNORECASE)

# Claude 구조화 출력이 지원하지 않는 제약. 빼도 각 기능의 출력 모델이 다시 검사한다.
UNSUPPORTED_KEYS = {
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "uniqueItems",
    "pattern",
    "default",
}


def clean_json_text(raw: str) -> str:
    """로컬 모델이 덧붙이는 생각 태그·코드 블록 표시만 걷어낸다."""
    text = THINK_BLOCK.sub("", raw).strip()
    if match := FENCE.match(text):
        text = match.group(1).strip()
    return text


def strict_schema(schema: dict) -> dict:
    """구조화 출력용 사본: 지원하지 않는 제약을 빼고 모든 객체를 닫는다."""

    def names(mapping):
        # properties·$defs의 키는 필드·정의 이름이므로 제약 이름과 같아도 지우지 않는다.
        return {key: walk(value) for key, value in mapping.items()}

    def walk(node):
        if isinstance(node, dict):
            cleaned = {}
            for key, value in node.items():
                if key in {"properties", "$defs"} and isinstance(value, dict):
                    cleaned[key] = names(value)
                elif key not in UNSUPPORTED_KEYS:
                    cleaned[key] = walk(value)
            if cleaned.get("type") == "object" or "properties" in cleaned:
                cleaned["additionalProperties"] = False
            return cleaned
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(copy.deepcopy(schema))
