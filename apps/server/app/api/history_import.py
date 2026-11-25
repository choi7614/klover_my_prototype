from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, model_validator

from app.api.mail_read import authorize
from app.api.state import StateName, get_state


class ImportRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: date
    end: date

    @model_validator(mode="after")
    def valid(self):
        if not self.start <= self.end <= datetime.now(
            ZoneInfo("Asia/Seoul")
        ).date() or self.end - self.start > timedelta(days=365):
            raise ValueError("기간은 오늘 이전의 최대 366일입니다")
        return self


class HistoryJobState(BaseModel):
    job_id: str
    start: date
    end: date
    status: Literal["running", "paused", "failed", "completed"]
    saved: int
    skipped: int
    processed: int
    error: str | None
    created_at: str


def public(data):
    return {k: v for k, v in data.items() if k not in {"page_token", "page_done", "run_id"}}


def register_history_import(app):
    router = APIRouter(
        prefix="/mail-history", tags=["과거 메일 가져오기"], dependencies=[Depends(authorize)]
    )

    def runner(request):
        result = get_state(request, StateName.HISTORY_IMPORT)
        if result is None:
            raise HTTPException(503)
        return result

    @router.get("", response_model=list[HistoryJobState])
    def listing(request: Request):
        return [public(x) for x in runner(request).repository.list()]

    @router.post("", status_code=201, response_model=HistoryJobState)
    def create(body: ImportRange, request: Request):
        run = runner(request)
        try:
            data = run.repository.create(body.start, body.end)
            return public(run.resume(data["job_id"]))
        except ValueError:
            raise HTTPException(409) from None

    @router.post("/{job_id}/{action}", response_model=HistoryJobState)
    def action(job_id: str, action: str, request: Request):
        run = runner(request)
        if action not in {"pause", "resume"}:
            raise HTTPException(422)
        try:
            data = (
                run.resume(job_id)
                if action == "resume"
                else run.repository.transition(job_id, "pause")
            )
        except ValueError:
            raise HTTPException(409) from None
        if data is None:
            raise HTTPException(404)
        return public(data)

    app.include_router(router)

    @app.middleware("http")
    async def private_history(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/mail-history"):
            response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        return response
