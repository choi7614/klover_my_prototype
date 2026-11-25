"""답장 초안의 근거 표시를 서버가 직접 계산한다.

AI에게 "본문의 이 문구는 이 메일에서 왔다"를 글자 하나 틀리지 않게 다시 베끼게 하면
LLM은 자주 틀린다(공백·따옴표·인용 칸 혼동). 그래서 AI는 본문·방향만 만들고,
근거는 여기서 본문과 실제 메일·학습 표현을 비교해 **확인된 것만** 표시한다.
꾸며낸 근거가 들어갈 수 없고, 못 찾으면 표시를 줄일 뿐 초안은 버리지 않는다.
이 근거는 '문구가 실제로 겹치는가'를 뜻하며 의미상 이유까지 증명하지는 않는다.
"""

import re
import unicodedata

from app.schemas.profile_draft import Evidence, GenerationInput

# 3글자 조각이 이만큼 이상 겹쳐야 같은 표현으로 본다. '감사합니다' 같은 흔한 인사말은 걸러진다.
GRAM = 3
MIN_SHARED = 6
MIN_CONTAINMENT = 0.2
MIN_SENTENCE_CHARS = 8
MAX_EVIDENCE = 100

_SENTENCE = re.compile(r"[^\n.!?。]+[.!?。]?")


def _plain(text: str) -> str:
    """띄어쓰기·문장부호·따옴표 모양 차이를 지우고 글자만 남긴다(비교 전용)."""
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text).casefold())


def _grams(text: str) -> frozenset[str]:
    plain = _plain(text)
    return frozenset(plain[i : i + GRAM] for i in range(len(plain) - GRAM + 1))


def _sentences(text: str):
    """(시작, 끝, 문장) — 앞뒤 공백을 뺀 문장과 원문 안 위치."""
    for match in _SENTENCE.finditer(text):
        raw = match.group()
        stripped = raw.strip()
        if not stripped:
            continue
        start = match.start() + (len(raw) - len(raw.lstrip()))
        yield start, start + len(stripped), stripped


def _overlaps(span, taken):
    return any(span[0] < other[1] and span[1] > other[0] for other in taken)


def phrase_evidence(body: str, learned_phrases) -> list[tuple[tuple[int, int], str]]:
    """본문에 그대로 들어 있는 학습 표현. 긴 표현부터 찾고 겹치는 위치는 쓰지 않는다."""
    found: list[tuple[tuple[int, int], str]] = []
    for phrase in sorted({p for p in learned_phrases if p}, key=len, reverse=True):
        start = body.find(phrase)
        while start >= 0:
            span = (start, start + len(phrase))
            if not _overlaps(span, [item[0] for item in found]):
                found.append((span, "profile.phrase"))
            start = body.find(phrase, start + len(phrase))
    return found


def mail_evidence(
    body: str, request: GenerationInput, blocked
) -> list[tuple[tuple[int, int], str]]:
    """본문 문장 중 입력 메일의 문장과 표현이 충분히 겹치는 것을 그 메일에 연결한다."""
    sources = []
    for mail in (request.original, *request.related):
        grams = [_grams(sentence) for _, _, sentence in _sentences(mail.subject)]
        grams += [_grams(sentence) for _, _, sentence in _sentences(mail.body_text)]
        sources.append((f"mail:{mail.mail_id}", [g for g in grams if g]))
    found: list[tuple[tuple[int, int], str]] = []
    for start, end, sentence in _sentences(body):
        if len(_plain(sentence)) < MIN_SENTENCE_CHARS or _overlaps((start, end), blocked):
            continue
        mine = _grams(sentence)
        best_key, best_source = (0, 0.0), None
        for source, grams_list in sources:
            for grams in grams_list:
                shared = len(mine & grams)
                key = (shared, shared / len(mine))
                if shared >= MIN_SHARED and key[1] >= MIN_CONTAINMENT and key > best_key:
                    best_key, best_source = key, source
        if best_source:
            found.append(((start, end), best_source))
    return found


def derive_evidence(body: str, request: GenerationInput) -> tuple[Evidence, ...]:
    items = phrase_evidence(body, request.learned_phrases)
    # 미리보기는 합성 메일만 쓰므로 메일 근거를 만들지 않는다.
    if request.purpose != "preview":
        items += mail_evidence(body, request, [item[0] for item in items])
    items.sort(key=lambda item: item[0])
    return tuple(Evidence(span=span, source=source) for span, source in items[:MAX_EVIDENCE])
