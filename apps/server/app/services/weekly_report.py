"""첫 단위의 입력을 재사용하는 생성·검증·저장·편집 서비스."""

import asyncio
import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import ValidationError

from app.ai.interfaces import ProviderCallError, ProvidersNotConfigured
from app.ai.weekly_report import WeeklyReportGenerator
from app.db.repositories.report_mail import ReportMailRepository
from app.db.repositories.weekly_report import (
    ReportConflictError,
    WeeklyReportRepository,
)
from app.schemas.report import REPORT_TIMEZONE, ReportPeriod
from app.schemas.weekly_report import (
    EditWeeklyReport,
    GeneratedReport,
    GenerateWeeklyReport,
    ReportActor,
    ReportItem,
    ReportSection,
    StoredWeeklyReport,
    WeeklyReportDocument,
    WeeklyReportOptions,
)
from app.services.report import prepare_weekly_report_input
from app.services.report_ports import ReportProfilePort


class WeeklyReportError(ValueError):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def _validate_sections(sections, source, expected_names):
    if tuple(section.name for section in sections) != tuple(expected_names):
        raise WeeklyReportError("invalid_report", "보고 섹션 이름과 순서를 확인해 주세요.", 422)
    allowed = {mail.mail_id for group in source.groups for mail in group.mails}
    item_ids = set()
    for section in sections:
        for item in section.items:
            if (
                not item.text.strip()
                or not item.evidence
                or len(set(item.evidence)) != len(item.evidence)
                or not set(item.evidence) <= allowed
                or item.item_id in item_ids
            ):
                raise WeeklyReportError(
                    "invalid_evidence", "모든 항목에 대상 업무 메일 근거를 연결해 주세요.", 422
                )
            item_ids.add(item.item_id)
    if allowed and not item_ids:
        raise WeeklyReportError("invalid_report", "근거가 있는 보고 항목이 필요합니다.", 422)


class WeeklyReportService:
    def __init__(
        self,
        *,
        mails: ReportMailRepository,
        profiles: ReportProfilePort,
        reports: WeeklyReportRepository,
        generator: WeeklyReportGenerator | None = None,
        now=None,
        timeout: float = 30,
        allow_test_results: bool | None = None,
    ):
        self.mails, self.profiles, self.reports, self.generator = (
            mails,
            profiles,
            reports,
            generator,
        )
        self.now = now or (lambda: datetime.now(UTC))
        self.timeout = timeout
        self.allow_test_results = (
            generator is not None and generator.mode == "test_double"
            if allow_test_results is None
            else allow_test_results
        )

    def _period(self):
        today = self.now().astimezone(REPORT_TIMEZONE).date()
        monday = today - timedelta(days=today.weekday() + 7)
        return ReportPeriod(start=monday, end=monday + timedelta(days=4))

    async def options(self, actor: ReportActor) -> WeeklyReportOptions:
        profile = await self.profiles.get_report_profile(user_id=actor.user_id)
        if profile is not None and profile.user_id != actor.user_id:
            raise WeeklyReportError("profile_unavailable", "보고 프로필을 확인해 주세요.", 503)
        available = actor.sync_started_at + timedelta(days=7)
        return WeeklyReportOptions(
            default_period=self._period(),
            profile=profile,
            remaining_days=max(0, math.ceil((available - self.now()).total_seconds() / 86400)),
            available_on=available.astimezone(REPORT_TIMEZONE).date(),
            generation=self.generator.mode if self.generator is not None else "unavailable",
        )

    def _check_stored(self, actor, stored):
        if (
            stored is None
            or stored.user_id != actor.user_id
            or stored.account_id != actor.account_id
        ):
            raise WeeklyReportError("not_found", "보고서를 찾을 수 없습니다.", 404)
        document, source = stored.document, stored.source
        if document.generation == "test_double" and not self.allow_test_results:
            raise WeeklyReportError(
                "ai_unavailable", "검토용 대역 결과는 운영 보고서로 사용할 수 없습니다.", 503
            )
        mails = [mail for group in source.groups for mail in group.mails]
        all_mails = mails + [item.mail for item in source.excluded]
        if (
            stored.profile.user_id != actor.user_id
            or document.period != source.period
            or document.scope != source.scope
            or document.evidence_mails != tuple(mails)
            or len({mail.mail_id for mail in all_mails}) != len(all_mails)
            or any(
                mail.user_id != actor.user_id
                or not source.period.start_at <= mail.received_at < source.period.end_before
                for mail in all_mails
            )
        ):
            raise WeeklyReportError("storage_unavailable", "저장된 보고서를 확인해 주세요.", 503)
        _validate_sections(document.sections, source, stored.profile.report_sections)
        return stored

    async def get(self, actor: ReportActor, report_id: str) -> WeeklyReportDocument:
        stored = await self.reports.get(user_id=actor.user_id, report_id=report_id)
        return self._check_stored(actor, stored).document

    async def excluded(self, actor: ReportActor, report_id: str):
        stored = await self.reports.get(user_id=actor.user_id, report_id=report_id)
        return self._check_stored(actor, stored).source.excluded

    async def generate(self, actor: ReportActor, request: GenerateWeeklyReport):
        options = await self.options(actor)
        if options.remaining_days:
            raise WeeklyReportError("report_not_ready", "사용 1주 후부터 만들 수 있어요.")
        profile = options.profile
        if profile is None:
            raise WeeklyReportError(
                "profile_missing", "주간 보고 프로필과 양식을 먼저 연결해 주세요."
            )
        period = (
            ReportPeriod(start=request.start, end=request.end)
            if request.start is not None
            else options.default_period
        )
        style = profile.report_style if request.template == "profile" else request.template
        recipient = request.recipient or profile.report_recipient
        if not recipient.strip():
            raise WeeklyReportError("profile_incomplete", "보고 대상을 입력해 주세요.")
        selection_key = hashlib.sha256(
            json.dumps(
                dict(
                    account_id=actor.account_id,
                    period=period.model_dump(mode="json"),
                    profile=profile.model_dump(mode="json"),
                    style=style,
                    recipient=recipient,
                ),
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        existing = await self.reports.find(user_id=actor.user_id, selection_key=selection_key)
        if existing is not None:
            self._check_stored(actor, existing)
            if not request.regenerate:
                return existing.document
            if request.expected_revision != existing.document.revision:
                raise ReportConflictError("저장본이 변경되었습니다. 다시 확인해 주세요")

        source = await prepare_weekly_report_input(
            repository=self.mails, user_id=actor.user_id, period=period
        )
        generation = "none"
        if not source.groups:
            sections = tuple(ReportSection(name=name, items=()) for name in profile.report_sections)
        else:
            if self.generator is None:
                raise WeeklyReportError(
                    "ai_unavailable", "보고서 AI가 아직 연결되지 않았습니다.", 503
                )
            try:
                raw = await asyncio.wait_for(
                    self.generator.generate(
                        source=source, profile=profile, style=style, recipient=recipient
                    ),
                    timeout=self.timeout,
                )
                if isinstance(raw, GeneratedReport):
                    raw = raw.model_dump(round_trip=True)
                generated = GeneratedReport.model_validate(raw)
                sections = tuple(
                    ReportSection(
                        name=section.name,
                        items=tuple(
                            ReportItem(item_id=uuid4().hex, **item.model_dump())
                            for item in section.items
                        ),
                    )
                    for section in generated.sections
                )
            except ProvidersNotConfigured:
                raise WeeklyReportError(
                    "ai_unavailable", "보고서 AI가 아직 연결되지 않았습니다.", 503
                ) from None
            except ProviderCallError:
                raise WeeklyReportError(
                    "ai_failed", "보고서를 만들지 못했어요. 기존 내용은 보존됩니다.", 502
                ) from None
            except ValidationError:
                raise WeeklyReportError(
                    "invalid_report", "생성 결과 형식과 근거를 확인하지 못했습니다.", 502
                ) from None
            except Exception:
                raise WeeklyReportError(
                    "ai_failed", "보고서를 만들지 못했어요. 기존 내용은 보존됩니다.", 502
                ) from None
            _validate_sections(sections, source, profile.report_sections)
            generation = self.generator.mode

        stamp = self.now()
        document = WeeklyReportDocument(
            report_id=existing.document.report_id if existing else uuid4().hex,
            revision=existing.document.revision + 1 if existing else 1,
            period=period,
            title=(
                f"{profile.org + ' ' if profile.org else ''}주간 업무 보고 "
                f"({period.start:%m/%d} – {period.end:%m/%d})"
            ),
            subtitle=(
                f"{profile.name} {profile.title} · "
                f"작성 {stamp.astimezone(REPORT_TIMEZONE):%Y.%m.%d}"
            ),
            recipient=recipient,
            style=style,
            sections=sections,
            scope=source.scope,
            evidence_mails=tuple(mail for group in source.groups for mail in group.mails),
            status="ready" if source.groups else "empty",
            generation=generation,
            created_at=existing.document.created_at if existing else stamp,
            updated_at=stamp,
        )
        stored = StoredWeeklyReport(
            user_id=actor.user_id,
            account_id=actor.account_id,
            selection_key=selection_key,
            profile=profile,
            source=source,
            document=document,
        )
        if existing:
            await self.reports.replace(stored, expected_revision=existing.document.revision)
        else:
            await self.reports.create(stored)
        return document

    async def edit(self, actor: ReportActor, report_id: str, request: EditWeeklyReport):
        stored = self._check_stored(
            actor, await self.reports.get(user_id=actor.user_id, report_id=report_id)
        )
        if request.expected_revision != stored.document.revision:
            raise ReportConflictError("저장본이 변경되었습니다. 다시 확인해 주세요")
        # 직접 서비스 호출도 HTTP와 같은 스키마 검증을 거친다.
        request = EditWeeklyReport.model_validate(request.model_dump(round_trip=True))
        _validate_sections(request.sections, stored.source, stored.profile.report_sections)
        document = stored.document.model_copy(
            update={
                "sections": request.sections,
                "revision": stored.document.revision + 1,
                "updated_at": self.now(),
            }
        )
        updated = stored.model_copy(update={"document": document})
        await self.reports.replace(updated, expected_revision=request.expected_revision)
        return document
