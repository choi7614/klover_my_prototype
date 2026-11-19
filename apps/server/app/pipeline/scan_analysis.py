"""F1 분석 결과(AnalysisResult) + 원본 본문 → F5 입력(ScanInput) 변환.

- 제안 내용(일정 제목·시각·장소, 할 일 제목·마감)은 F1 결과를 그대로 쓴다. AI가 바꾸지 않는다.
- AI(purpose=scan)에는 '각 항목의 근거 문장을 원문 그대로 인용'과 회신 이유만 맡긴다.
- 인용문이 원문에 실제로 있는지 F5가 직접 찾아 위치(코드 포인트 [start,end))를 정한다.
- 형식을 어기거나 없는 인용을 주면 한 번 다시 묻고, 그래도 없는 항목은 버린다(지어내지 않음).
- 오류 메시지·로그에 본문·인용문·외부 응답 원문을 넣지 않는다.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.ai.interfaces import GenerationRequest, TextGeneration
from app.ai.json_output import clean_json_text
from app.schemas.f5 import (
    CalendarPayload,
    ScanInput,
    TodoPayload,
)
from app.schemas.f5_scan import ScanLinks, SkippedItem
from app.schemas.mail_analysis import AnalysisResult

PROMPT = Path(__file__).resolve().parents[1] / "ai/prompts/scan.md"
MAX_ATTEMPTS = 2
MAX_BODY = 200_000
MAX_RESPONSE = 200_000
TITLE_LIMIT = 300

# F5 제안 유형 ↔ F1 근거 종류. 같은 위치를 우선 고르는 데만 쓴다.
HINT_KINDS = {"calendar": {"event"}, "todo": {"action", "due"}, "reply": {"action", "due", "event"}}


class ScanFailed(Exception):
    """고정 코드만 담는다. provider_error / timeout / invalid_response / ..."""

    def __init__(self, code: str, attempts: int = 0):
        self.code = code
        self.attempts = attempts
        super().__init__(code)


class _Retry(Exception):
    def __init__(self, reason: str):
        self.reason = reason


@dataclass(frozen=True)
class ScanBuild:
    scan_input: ScanInput
    skipped: tuple[SkippedItem, ...]
    attempts: int

    @property
    def has_candidates(self) -> bool:
        value = self.scan_input
        return bool(value.events or value.action_items or value.reply)


def body_sha256(body_text: str) -> str:
    return hashlib.sha256(body_text.encode()).hexdigest()


def action_key(kind: str, start: int, end: int) -> str:
    # 근거 위치로 만든 키다. 재분석으로 문구가 바뀌어도 같은 문장이면 같은 제안으로 본다.
    return f"{kind}-" + hashlib.sha256(f"{start}:{end}".encode()).hexdigest()[:32]


def _eligible(analysis: AnalysisResult):
    """F1 항목 중 F5 계약을 채울 수 있는 것만 고른다. 나머지는 이유와 함께 건너뛴다."""
    events, todos, skipped = {}, {}, []
    for index, event in enumerate(analysis.events):
        if event.end is None:
            skipped.append(SkippedItem(type="calendar", index=index, reason="event_end_unknown"))
        elif len(event.title) > TITLE_LIMIT:
            skipped.append(SkippedItem(type="calendar", index=index, reason="title_too_long"))
        else:
            events[index] = CalendarPayload(
                title=event.title,
                start=event.start,
                end=event.end,
                location=event.location or "",
            )
    for index, item in enumerate(analysis.action_items):
        if len(item.text) > TITLE_LIMIT:
            skipped.append(SkippedItem(type="todo", index=index, reason="title_too_long"))
        else:
            todos[index] = TodoPayload(title=item.text, due=item.due)
    return events, todos, skipped


def _prompt_payload(analysis, body_text, events, todos):
    return {
        "mail_id": analysis.mail_id,
        "body_text": body_text,
        "events": [
            {
                "index": index,
                "title": payload.title,
                "start": payload.start.isoformat(),
                "end": payload.end.isoformat(),
                "location": payload.location or None,
            }
            for index, payload in events.items()
        ],
        "action_items": [
            {
                "index": index,
                "text": payload.title,
                "due": payload.due.isoformat() if payload.due else None,
            }
            for index, payload in todos.items()
        ],
        "needs_reply": analysis.needs_reply,
        "evidence_hints": [
            {"kind": span.kind, "text": body_text[span.start : span.end]}
            for span in analysis.evidence_spans
        ],
    }


class _Locator:
    """인용문을 원문에서 찾아 위치를 정한다. 같은 유형 안에서 같은 위치를 두 번 쓰지 않는다."""

    def __init__(self, body_text: str, analysis: AnalysisResult):
        self.body = body_text
        self.hints = analysis.evidence_spans
        self.used: dict[str, set[tuple[int, int]]] = {
            "calendar": set(),
            "todo": set(),
            "reply": set(),
        }

    def find(self, kind: str, quote: str):
        """(start, end) 또는 실패 이유를 돌려준다."""
        text = quote.strip()
        if not text:
            return "evidence_not_found"
        positions = []
        start = self.body.find(text)
        while start != -1:
            positions.append((start, start + len(text)))
            start = self.body.find(text, start + 1)
        if not positions:
            return "evidence_not_found"
        kinds = HINT_KINDS[kind]

        def overlaps_hint(position):
            return any(
                span.kind in kinds and span.start < position[1] and position[0] < span.end
                for span in self.hints
            )

        # F1이 같은 종류로 표시한 위치와 겹치는 곳을 먼저, 그다음 본문 앞쪽부터 고른다.
        for position in sorted(positions, key=lambda p: (not overlaps_hint(p), p)):
            if position not in self.used[kind]:
                self.used[kind].add(position)
                return position
        return "duplicate_evidence"


def _span(mail_id, body_text, position):
    start, end = position
    return {"mail_id": mail_id, "start": start, "end": end, "quote": body_text[start:end]}


def _parse(raw, analysis, events, todos):
    """형식 검사. 형식이 틀리면 _Retry('invalid_response')."""
    if not isinstance(raw, str) or len(raw) > MAX_RESPONSE:
        raise _Retry("invalid_response")
    try:
        links = ScanLinks.model_validate_json(clean_json_text(raw), strict=True)
    except (ValidationError, ValueError):
        raise _Retry("invalid_response") from None
    if links.mail_id != analysis.mail_id:
        raise _Retry("invalid_response")
    for items, allowed in ((links.events, events), (links.action_items, todos)):
        indexes = [item.index for item in items]
        if len(set(indexes)) != len(indexes) or any(index not in allowed for index in indexes):
            raise _Retry("invalid_response")
    if links.reply is not None and (not analysis.needs_reply or not links.reply.reason.strip()):
        raise _Retry("invalid_response")
    return links


def _assemble(links, analysis, body_text, events, todos, *, final):
    """근거 위치를 확정해 ScanInput 조각을 만든다.

    마지막 시도가 아니면 빠진 근거가 있을 때 다시 묻는다.
    """
    locator = _Locator(body_text, analysis)
    built = {"events": [], "action_items": [], "reply": None}
    skipped = []
    by_type = (
        ("calendar", "events", events, {item.index: item.quote for item in links.events}),
        ("todo", "action_items", todos, {item.index: item.quote for item in links.action_items}),
    )
    for kind, field, payloads, quotes in by_type:
        for index, payload in payloads.items():
            quote = quotes.get(index)
            found = "evidence_missing" if quote is None else locator.find(kind, quote)
            if isinstance(found, str):
                skipped.append(SkippedItem(type=kind, index=index, reason=found))
                continue
            built[field].append(
                {
                    "action_key": action_key(kind, *found),
                    "evidence_spans": [_span(analysis.mail_id, body_text, found)],
                    "payload": payload.model_dump(mode="json"),
                }
            )
    if analysis.needs_reply:
        found = (
            "evidence_missing" if links.reply is None else locator.find("reply", links.reply.quote)
        )
        if isinstance(found, str):
            skipped.append(SkippedItem(type="reply", index=None, reason=found))
        else:
            built["reply"] = {
                "action_key": action_key("reply", *found),
                "evidence_spans": [_span(analysis.mail_id, body_text, found)],
                "payload": {"reason": links.reply.reason.strip()},
            }
    if skipped and not final:
        # 로컬 모델은 인용문을 살짝 바꾸거나 빠뜨리기 쉽다. 한 번만 다시 묻는다.
        raise _Retry("evidence_not_found")
    return built, skipped


async def build_scan_input(
    mail_id: str,
    body_text: str,
    analysis: AnalysisResult,
    generator: TextGeneration | None,
    *,
    timeout: float = 20,
) -> ScanBuild:
    analysis = AnalysisResult.model_validate(analysis)
    if analysis.mail_id != mail_id:
        raise ScanFailed("analysis_mismatch")
    if len(body_text) > MAX_BODY:
        raise ScanFailed("input_too_large")
    if any(span.end > len(body_text) for span in analysis.evidence_spans):
        # 분석 뒤 본문이 바뀌었거나 다른 본문 기준 결과다.
        raise ScanFailed("analysis_mismatch")
    events, todos, skipped = _eligible(analysis)
    base = {"mail_id": mail_id, "body_sha256": body_sha256(body_text)}
    if not events and not todos and not analysis.needs_reply:
        # 제안할 것이 없으면 AI를 부르지 않는다.
        return ScanBuild(ScanInput.model_validate(base), tuple(skipped), 0)
    if generator is None:
        raise ScanFailed("provider_not_configured")
    payload = _prompt_payload(analysis, body_text, events, todos)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = GenerationRequest(
            purpose="scan",
            system_prompt=PROMPT.read_text(encoding="utf-8"),
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_schema=ScanLinks.model_json_schema(),
        )
        try:
            raw = await asyncio.wait_for(generator.generate(request), timeout)
        except TimeoutError:
            raise ScanFailed("timeout", attempt) from None
        except Exception:
            raise ScanFailed("provider_error", attempt) from None
        final = attempt == MAX_ATTEMPTS
        try:
            links = _parse(raw, analysis, events, todos)
            built, missing = _assemble(links, analysis, body_text, events, todos, final=final)
        except _Retry as retry:
            if final:
                # 마지막 시도까지 형식을 어기면 아무 제안도 만들지 않는다.
                raise ScanFailed(retry.reason, attempt) from None
            payload["retry_reason"] = retry.reason
            continue
        scan_input = ScanInput.model_validate({**base, **built})
        return ScanBuild(scan_input, tuple(skipped + missing), attempt)
    raise AssertionError("도달할 수 없는 스캔 경로")
