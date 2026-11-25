"""서버가 계산하는 답장 근거: 겹치는 표현만 연결하고, 없는 근거는 만들지 않는다. 외부 호출 없음."""

from datetime import UTC, datetime

import pytest

from app.ai.f2_evidence import derive_evidence
from app.schemas.profile_draft import DraftMail, GenerationInput, Profile

MAIL = "안녕하세요.\n3분기 부서별 예산 집행 현황 자료를 금요일까지 보내 주세요.\n감사합니다."
REPLY = "요청하신 3분기 부서별 예산 집행 현황 자료는 확인 후 공유드리겠습니다."


def mail(mail_id="m1", subject="자료 요청", body=MAIL):
    return DraftMail(
        mail_id=mail_id,
        subject=subject,
        body_text=body,
        from_addr="a@example.invalid",
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def request(related=(), phrases=(), purpose="draft", original=None):
    return GenerationInput(
        original=original or mail(),
        related=tuple(related),
        profile=Profile(),
        learned_phrases=tuple(phrases),
        purpose=purpose,
    )


def texts(body, result):
    return [(body[e.span[0] : e.span[1]], e.source) for e in result]


def test_reply_sentence_that_reuses_mail_wording_is_linked_to_that_mail():
    body = "안녕하세요.\n" + REPLY
    assert texts(body, derive_evidence(body, request())) == [(REPLY, "mail:m1")]


@pytest.mark.parametrize(
    "variant",
    [
        REPLY.replace("현황 ", "현황\n"),  # 중간에 줄이 바뀌어도
        REPLY.replace("요청하신 ", "'요청하신' "),  # 따옴표를 붙여도
        REPLY.replace("3분기", "３분기"),  # 전각 숫자여도(같은 글자로 본다)
    ],
)
def test_spacing_quotes_and_width_differences_do_not_hide_a_real_overlap(variant):
    # 줄바꿈이 많으면 문장이 여러 조각이 될 수 있어, 한 조각이라도 연결되면 충분하다.
    assert any(src == "mail:m1" for _, src in texts(variant, derive_evidence(variant, request())))


@pytest.mark.parametrize(
    "body",
    [
        "감사합니다.",  # 흔한 인사말
        "안녕하세요. 잘 지내시죠?",
        "내일 점심은 김치찌개가 좋겠습니다.",  # 상관없는 문장
        "네.",
    ],
)
def test_greetings_and_unrelated_sentences_are_not_linked(body):
    assert derive_evidence(body, request()) == ()


def test_each_sentence_links_to_the_best_matching_mail_among_related():
    other = mail("m2", "일정", "다음 주 화요일 오후 두 시에 분기 마감 회의를 진행합니다.")
    body = REPLY + "\n다음 주 화요일 오후 두 시 분기 마감 회의에 참석하겠습니다."
    got = texts(body, derive_evidence(body, request(related=[other])))
    assert got == [
        (REPLY, "mail:m1"),
        ("다음 주 화요일 오후 두 시 분기 마감 회의에 참석하겠습니다.", "mail:m2"),
    ]


def test_preview_never_links_mail_evidence():
    assert derive_evidence(REPLY, request(purpose="preview")) == ()


def test_learned_phrases_are_marked_only_where_they_appear_exactly():
    body = "요청 내용 확인했습니다. 확인 후 회신드리겠습니다."
    got = texts(body, derive_evidence(body, request(phrases=["확인 후 회신드리겠습니다."])))
    assert got == [("확인 후 회신드리겠습니다.", "profile.phrase")]
    assert derive_evidence(body, request(phrases=["없는 표현입니다"])) == ()


def test_phrase_and_mail_evidence_never_overlap_and_are_ordered():
    phrase = "공유드리겠습니다."
    body = f"{REPLY}\n별도 문의는 언제든 편하게 연락 주세요. {phrase}"
    result = derive_evidence(body, request(phrases=[phrase]))
    spans = [e.span for e in result]
    assert spans == sorted(spans)
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:], strict=False))
    assert ("profile.phrase" in [e.source for e in result]) is True


def test_sources_are_always_input_mails_and_spans_stay_inside_the_body():
    other = mail(
        "m2", "다른 건", "예산 집행 현황 자료 공유 요청 건입니다. 부서별 일정 확인 바랍니다."
    )
    body = REPLY + "\n" + "예산 집행 현황 자료 공유 요청 건은 부서별 일정 확인 후 알려드립니다."
    result = derive_evidence(body, request(related=[other], phrases=["알려드립니다."]))
    allowed = {"mail:m1", "mail:m2", "profile.phrase"}
    assert result and all(e.source in allowed for e in result)
    assert all(0 <= e.span[0] < e.span[1] <= len(body) for e in result)


def test_empty_or_short_inputs_do_not_break():
    assert derive_evidence("네", request()) == ()
    assert (
        derive_evidence("가나다라마바사아자차", request(original=mail(body="", subject=""))) == ()
    )
