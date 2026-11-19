"""F5 승인 경계. 생성·조회는 어떤 행동도 실행하지 않는다."""

from pydantic import ValidationError

from app.pipeline.scan import scan
from app.schemas.f5 import CalendarPayload, ExecutionReceipt, ReplyPayload, TodoPayload
from app.services.calendar import BlockedCalendar, event_id
from app.services.f5_errors import CalendarError, F5Error


class F5Service:
    def __init__(self, repository, calendar=None):
        self.repository = repository
        self.calendar = calendar if calendar is not None else BlockedCalendar()

    def scan(self, owner, analysis):
        return scan(self.repository, owner, analysis)

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

    def conflicts(self, owner, suggestion_id, payload):
        row = self.repository.get(owner, suggestion_id)
        if row.type != "calendar":
            raise F5Error("invalid_suggestion_type", 422)
        return self.calendar.conflicts(owner, payload)
