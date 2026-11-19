"""오류에는 메일·토큰·외부 응답 원문을 담지 않는다."""


class F5Error(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status
        super().__init__(code)


class CalendarError(F5Error):
    def __init__(self, code: str, *, uncertain: bool = False, blocked: bool = False):
        super().__init__(code, 503 if blocked else 502)
        self.uncertain, self.blocked = uncertain, blocked
