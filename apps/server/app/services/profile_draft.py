"""F2 처리: 검증된 메일·설정만 AI 포트에 전달하고 근거와 본문을 확인한다."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError

from app.ai.f2_port import DraftAI, F2Error, RelatedMailSearch
from app.db.repositories.mail_query import MailAccountUnavailable
from app.db.repositories.profile_draft import F2Repository, conflict
from app.schemas.profile_draft import (
    ContextStatus,
    DraftCreate,
    DraftMail,
    DraftRevise,
    DraftSave,
    DraftState,
    Evidence,
    GeneratedDraft,
    GenerationInput,
    PreviewState,
    Profile,
    Reference,
)

AI_TIMEOUT_SECONDS = 8
PREVIEW_TIMEOUT_SECONDS = 2


def invalid_output():
    return F2Error("invalid_ai_output", 502, "AI 결과의 본문과 근거를 확인하지 못했어요.")


def compose(result: GeneratedDraft, request: GenerationInput):
    """고정 인사·마무리·서명은 모델에 맡기지 않고 그대로 붙인다."""
    body, evidence = "", []
    allowed = {mail.mail_id for mail in (request.original, *request.related)}
    previous_end = 0
    for item in result.evidence:
        start, end = item.span
        if not 0 <= start < end <= len(result.body) or start < previous_end:
            raise invalid_output()
        previous_end = end
        if item.source.startswith("mail:"):
            if item.source[5:] not in allowed:
                raise invalid_output()
        elif (
            item.source != "profile.phrase" or result.body[start:end] not in request.learned_phrases
        ):
            raise invalid_output()

    if request.profile.greeting:
        body = request.profile.greeting
        evidence.append(Evidence(span=(0, len(body)), source="profile.greeting"))
        body += "\n\n"
    offset = len(body)
    body += result.body
    evidence.extend(
        Evidence(span=(e.span[0] + offset, e.span[1] + offset), source=e.source)
        for e in result.evidence
    )
    for key in ("closing", "signature"):
        value = getattr(request.profile, key)
        if value:
            body += "\n\n"
            start = len(body)
            body += value
            evidence.append(Evidence(span=(start, len(body)), source=f"profile.{key}"))
    return body, tuple(evidence)


class F2Service:
    def __init__(
        self,
        *,
        repository: F2Repository,
        mail_reader,
        owner,
        ai: DraftAI,
        related: RelatedMailSearch | None = None,
    ):
        self.repository, self.mail_reader, self.owner = repository, mail_reader, owner
        self.ai, self.related = ai, related

    def read_mail(self, mail_id: str) -> DraftMail:
        try:
            mail = self.mail_reader.detail(mail_id)
        except MailAccountUnavailable:
            raise F2Error("mail_unavailable", 503, "연결한 메일 계정을 확인해 주세요.") from None
        if mail is None:
            raise F2Error("not_found", 404, "메일을 찾을 수 없습니다.")
        # 기존 인증된 조회 계약을 재사용한다. 없는 F1 요청사항은 만들어 넣지 않는다.
        return DraftMail.model_validate(
            mail.model_dump(include=set(DraftMail.model_fields) - {"action_items"})
        )

    async def _generate(self, request: GenerationInput):
        try:
            timeout = (
                PREVIEW_TIMEOUT_SECONDS if request.purpose == "preview" else AI_TIMEOUT_SECONDS
            )
            async with asyncio.timeout(timeout):
                raw = await self.ai.generate(request)
            result = GeneratedDraft.model_validate(
                raw.model_dump() if isinstance(raw, GeneratedDraft) else raw
            )
        except F2Error:
            raise
        except TimeoutError:
            raise F2Error(
                "ai_timeout", 504, "생성 시간이 길어졌어요. 다시 시도해 주세요."
            ) from None
        except ValidationError:
            raise invalid_output() from None
        except Exception:
            raise F2Error(
                "ai_failed", 502, "초안을 만들지 못했어요. 직접 작성할 수 있어요."
            ) from None
        if request.direction is not None and result.selected_direction != request.direction:
            raise invalid_output()
        if any(phrase in result.body for phrase in request.profile.excluded_phrases):
            raise invalid_output()
        return result, compose(result, request)

    async def preview(self, profile: Profile) -> PreviewState:
        # 저장되지 않은 동의나 표현을 학습 결과에 접근하는 권한으로 사용하지 않는다.
        request = GenerationInput(
            purpose="preview",
            profile=profile.model_copy(update={"style_learning_enabled": False}),
            original=DraftMail(
                mail_id="preview-synthetic",
                subject="합성 자료 확인 요청",
                body_text="자료를 확인한 뒤 회신해 주세요. 실제 메일이 아닌 고정 예시입니다.",
                from_addr="preview@example.invalid",
                received_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
        result, (body, evidence) = await self._generate(request)
        if any(item.source.startswith("mail:") for item in result.evidence):
            raise invalid_output()
        return PreviewState(body=body, evidence=evidence)

    async def context(self, mail_id):
        original = self.read_mail(mail_id)
        related, status = (), "unavailable"
        if self.related is not None:
            identifiers = await self.related.find_ids(
                user_id=self.owner.user_id, account_id=self.owner.account_id, mail_id=mail_id
            )
            if len(identifiers) > 50 or len(set(identifiers)) != len(identifiers):
                raise invalid_output()
            related = tuple(
                self.read_mail(identifier) for identifier in identifiers if identifier != mail_id
            )
            status = "ready" if related else "empty"
        profile = self.repository.profile(user_id=self.owner.user_id)
        if not profile.exists:
            raise F2Error("profile_required", 409, "내 프로필을 먼저 저장해 주세요.")
        style = self.repository.style(user_id=self.owner.user_id, profile=profile.profile)
        return (
            GenerationInput(
                original=original,
                related=related,
                profile=profile.profile,
                learned_phrases=style.phrases,
                style_traits=style.traits,
            ),
            profile.version,
            ContextStatus(related=status),
        )

    async def create(self, request: DraftCreate) -> DraftState:
        context, version, status = await self.context(request.mail_id)
        context = context.model_copy(update={"direction": request.direction})
        result, (body, evidence) = await self._generate(context)
        self.ensure_current(context, version)
        draft = DraftState(
            draft_id="draft_" + uuid4().hex,
            mail_id=request.mail_id,
            directions=result.directions,
            selected_direction=result.selected_direction,
            body=body,
            evidence=evidence,
            references=self._references(context, evidence),
            version=1,
            profile_version=version,
            context_status=status,
        )
        return self.repository.save_draft(user_id=self.owner.user_id, draft=draft)

    def ensure_current(self, context, version):
        # 생성 대기 중 학습 동의·프로필·메일 접근이 바뀌면 이전 설정 결과를 저장하지 않는다.
        if self.repository.profile(user_id=self.owner.user_id).version != version:
            raise F2Error(
                "profile_changed", 409, "프로필이 바뀌었어요. 새 설정으로 다시 만들어 주세요."
            )
        for mail in (context.original, *context.related):
            self.read_mail(mail.mail_id)

    @staticmethod
    def _references(context, evidence):
        used = {e.source[5:] for e in evidence if e.source.startswith("mail:")}
        return tuple(
            Reference(mail_id=mail.mail_id, subject=mail.subject, received_at=mail.received_at)
            for mail in (context.original, *context.related)
            if mail.mail_id in used
        )

    def draft(self, draft_id):
        draft = self.repository.draft(user_id=self.owner.user_id, draft_id=draft_id)
        self.read_mail(draft.mail_id)
        for reference in draft.references:
            self.read_mail(reference.mail_id)
        return draft

    def save(self, draft_id: str, request: DraftSave):
        previous = self.draft(draft_id)
        if previous.version != request.expected_version:
            raise conflict()
        # 편집한 위치의 근거만 보존한다. 입력한 문자열은 HTML로 해석하지 않는다.
        evidence = preserve_evidence(previous.body, request.body, previous.evidence)
        used = {e.source[5:] for e in evidence if e.source.startswith("mail:")}
        updated = previous.model_copy(
            update={
                "body": request.body,
                "evidence": evidence,
                "references": tuple(r for r in previous.references if r.mail_id in used),
                "version": previous.version + 1,
            }
        )
        return self.repository.save_draft(
            user_id=self.owner.user_id, draft=updated, expected_version=previous.version
        )

    async def revise(self, draft_id: str, request: DraftRevise):
        previous = self.draft(draft_id)
        if previous.version != request.expected_version:
            raise conflict()
        direction = request.direction or previous.selected_direction
        if direction not in previous.directions:
            raise F2Error("invalid_direction", 422, "표시된 답장 방향을 선택해 주세요.")
        context, version, status = await self.context(previous.mail_id)
        context = context.model_copy(
            update={"direction": direction, "action": request.action, "current_body": request.body}
        )
        result, (body, evidence) = await self._generate(context)
        self.ensure_current(context, version)
        updated = previous.model_copy(
            update={
                "body": body,
                "evidence": evidence,
                "references": self._references(context, evidence),
                "directions": result.directions,
                "selected_direction": result.selected_direction,
                "version": previous.version + 1,
                "profile_version": version,
                "context_status": status,
            }
        )
        return self.repository.save_draft(
            user_id=self.owner.user_id, draft=updated, expected_version=previous.version
        )


def preserve_evidence(before, after, evidence):
    prefix = 0
    while prefix < min(len(before), len(after)) and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < min(len(before), len(after)) - prefix
        and before[len(before) - 1 - suffix] == after[len(after) - 1 - suffix]
    ):
        suffix += 1
    shift = len(after) - len(before)
    kept = []
    for item in evidence:
        if item.span[1] <= prefix:
            kept.append(item)
        elif item.span[0] >= len(before) - suffix:
            kept.append(
                item.model_copy(update={"span": (item.span[0] + shift, item.span[1] + shift)})
            )
    return tuple(kept)
