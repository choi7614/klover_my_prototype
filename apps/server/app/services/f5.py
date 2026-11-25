"""F5 승인 경계. 생성·조회는 어떤 행동도 실행하지 않는다."""

from pydantic import ValidationError

from app.ai.interfaces import ProvidersNotConfigured
from app.ai.runtime import is_external
from app.pipeline.scan import scan
from app.pipeline.scan_analysis import ScanFailed, build_scan_input
from app.schemas.f5 import (
    CalendarPayload,
    ExecutionReceipt,
    Principal,
    ReplyPayload,
    ScanResult,
    TodoPayload,
)
from app.schemas.f5_scan import AnalysisScanOutcome, AnalysisScanResult
from app.schemas.mail_analysis import AnalysisMail, AnalysisResult
from app.services.calendar import BlockedCalendar, event_id
from app.services.f5_errors import CalendarError, F5Error


class F5Service:
    def __init__(self, repository, calendar=None):
        self.repository = repository
        self.calendar = calendar if calendar is not None else BlockedCalendar()

    def scan(self, owner, analysis):
        return scan(self.repository, owner, analysis)

    async def scan_from_analysis(
        self,
        owner,
        mail_id,
        analysis,
        generator,
        *,
        allow_gmail=False,
        allow_test_provider=False,
        timeout=None,
    ) -> AnalysisScanResult:
        """F1 분석 결과로 제안을 만든다(저장만, 실행 없음). 같은 메일을 다시 넣어도 중복되지 않는다.

        - owner는 신뢰한 작업 컨텍스트(F1 작업의 사용자·계정)에서만 받는다.
        - generator는 공통 TextGeneration(purpose=scan). 제안할 것이 없으면 부르지 않는다.
        - 실제 Gmail 본문은 allow_gmail일 때만, 외부 전송 제공자(Claude)로는 보내지 않는다.
        """
        owner = Principal.model_validate(owner)
        analysis = AnalysisResult.model_validate(analysis)
        body_text, source = self.repository.scan_source(owner, mail_id)
        if generator is not None:
            if generator.identity.mode == "test" and not allow_test_provider:
                raise ProvidersNotConfigured("기본 실행에서는 테스트 제공자를 사용하지 않습니다")
            if source != "fixture" and (not allow_gmail or is_external(generator)):
                # 보안 확인 전까지 실제 Gmail 본문을 외부 AI로 보내지 않는다(open-questions 14).
                raise ScanFailed("external_transfer_blocked")
        elif source != "fixture" and not allow_gmail:
            raise ScanFailed("external_transfer_blocked")
        if timeout is None:
            timeout = _call_timeout(generator)
        build = await build_scan_input(mail_id, body_text, analysis, generator, timeout=timeout)
        if not build.has_candidates:
            return AnalysisScanResult(
                status="nothing_to_suggest",
                result=ScanResult(items=[], created_ids=[]),
                skipped=build.skipped,
                attempts=build.attempts,
            )
        result = self.scan(owner, build.scan_input)
        return AnalysisScanResult(
            status="created" if result.created_ids else "unchanged",
            result=result,
            skipped=build.skipped,
            attempts=build.attempts,
        )

    @staticmethod
    def _payload(row, override):
        model = {"calendar": CalendarPayload, "todo": TodoPayload, "reply": ReplyPayload}[row.type]
        try:
            value = row.payload.model_dump(mode="json") if override is None else override
            return model.model_validate(value)
        except ValidationError:
            raise F5Error("invalid_payload", 422) from None

    def approve(self, owner, suggestion_id, request):
        row = self.repository.get(owner, suggestion_id)
        payload = self._payload(row, request.payload)
        serialized = payload.model_dump(mode="json")
        if row.type == "todo":
            return self.repository.approve_todo(owner, suggestion_id, request.version, serialized)
        current, token = self.repository.claim(owner, suggestion_id, request.version, serialized)
        if token is None:
            return current
        try:
            if row.type == "reply":
                raise CalendarError("reply_executor_not_connected", blocked=True)
            receipt = self.calendar.execute(owner, suggestion_id, payload)
            if (
                not isinstance(receipt, ExecutionReceipt)
                or receipt.mode not in {"test", "live"}
                or receipt.external_id != event_id(suggestion_id)
            ):
                raise CalendarError("calendar_result_unknown", uncertain=True)
        except CalendarError as error:
            # 재조회가 실패해도 앞선 요청의 불명확함은 사라지지 않는다.
            # 이 잠금을 풀면 다른 캘린더로 재시도해 중복 등록할 수 있다.
            if row.execution_status == "uncertain" and not error.uncertain:
                error = CalendarError(error.code, uncertain=True, blocked=error.blocked)
            self.repository.finish(owner, suggestion_id, token, error=error)
            raise error
        except Exception:
            # 주입 실행기의 예기치 않은 오류도 이미 실행됐을 수 있어 안전한 실패로 간주하지 않는다.
            error = CalendarError("calendar_result_unknown", uncertain=True)
            self.repository.finish(owner, suggestion_id, token, error=error)
            raise error from None
        return self.repository.finish(owner, suggestion_id, token, receipt=receipt)

    def reregister(self, owner, suggestion_id, version):
        """이미 등록했지만 사용자가 구글 캘린더에서 지운 일정을 사용자 요청으로 다시 등록한다.

        - 아직 캘린더에 있으면 아무것도 만들지 않는다(calendar_event_exists).
        - 새 일정 ID는 (제안, 현재 버전)으로 정해져서 같은 요청을 다시 보내도 한 번만 만들어진다.
        - 처음 등록한 내용(승인 당시 payload)을 그대로 쓴다. 수정은 받지 않는다.
        """
        row = self.repository.get(owner, suggestion_id)
        if (
            row.type != "calendar"
            or row.status != "approved"
            or row.execution_status != "succeeded"
            or row.execution_mode != "live"
            or row.result is None
            or not row.result.external_id
        ):
            raise F5Error("reregister_not_available")
        if row.version != version:
            raise F5Error("stale_version")
        payload = CalendarPayload.model_validate(row.payload.model_dump(mode="json"))
        if self.calendar.registered(owner, payload, row.result.external_id):
            raise F5Error("calendar_event_exists")
        key = f"{suggestion_id}:re{row.version}"
        try:
            receipt = self.calendar.execute(owner, suggestion_id, payload, event_key=key)
        except CalendarError:
            raise
        except Exception:
            raise CalendarError("calendar_result_unknown", uncertain=True) from None
        if (
            not isinstance(receipt, ExecutionReceipt)
            or receipt.mode != "live"
            or receipt.external_id != event_id(key)
        ):
            raise CalendarError("calendar_result_unknown", uncertain=True)
        return self.repository.finish_reregister(owner, suggestion_id, version, receipt)

    def conflicts(self, owner, suggestion_id, payload):
        row = self.repository.get(owner, suggestion_id)
        if row.type != "calendar":
            raise F5Error("invalid_suggestion_type", 422)
        return self.calendar.conflicts(owner, payload)


def _call_timeout(provider) -> float:
    # 제공자가 알려 준 시간 제한(재시도 포함)을 쓴다. 로컬 모델은 20초보다 느릴 수 있다.
    value = getattr(provider, "call_timeout", None)
    if isinstance(value, int | float) and not isinstance(value, bool) and 0 < value <= 7200:
        return float(value)
    return 20.0


class AnalysisScanHook:
    """F1 '분석 완료 알림 지점'(on_analyzed)에 등록할 콜백.

    hook = AnalysisScanHook(F5Service(F5Repository(engine)), load_generation())
    await hook(mail, result)   # mail: AnalysisMail, result: AnalysisResult

    실패해도 예외를 던지지 않고 결과(status=failed, 고정 코드)를 돌려준다.
    F5 실패가 이미 확정된 F1 분석 저장을 되돌리지 않게 하기 위해서다.
    """

    def __init__(self, service, generator, *, allow_gmail=False, allow_test_provider=False):
        self.service = service
        self.generator = generator
        self.allow_gmail = allow_gmail
        self.allow_test_provider = allow_test_provider

    async def __call__(self, mail, result) -> AnalysisScanOutcome:
        mail = AnalysisMail.model_validate(mail)
        owner = Principal(user_id=mail.user_id, account_id=mail.account_id)
        try:
            outcome = await self.service.scan_from_analysis(
                owner,
                mail.mail_id,
                result,
                self.generator,
                allow_gmail=self.allow_gmail,
                allow_test_provider=self.allow_test_provider,
            )
        except ScanFailed as error:
            return _failed(mail.mail_id, error.code)
        except ProvidersNotConfigured:
            return _failed(mail.mail_id, "provider_not_configured")
        except F5Error as error:
            return _failed(mail.mail_id, error.code)
        except Exception:
            return _failed(mail.mail_id, "scan_unavailable")
        return AnalysisScanOutcome(
            mail_id=mail.mail_id,
            status=outcome.status,
            created=len(outcome.result.created_ids),
            skipped=len(outcome.skipped),
        )


def _failed(mail_id, code):
    return AnalysisScanOutcome(mail_id=mail_id, status="failed", failure_code=code)
