"""Calendar 조회·해제는 기존 Bearer/loopback 인증을 공유한다."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.f5 import Owner, Service


class CalendarOption(BaseModel):
    id: str
    label: str
    timezone: str


class CalendarConnection(BaseModel):
    status: str
    email: str
    calendars: list[CalendarOption]


router = APIRouter(prefix="/calendar", tags=["F5 Calendar"])


@router.get("/connection", response_model=CalendarConnection)
def connection(owner: Owner, service: Service):
    return service.calendar.status(owner)


@router.post("/disconnect", response_model=CalendarConnection)
def disconnect(owner: Owner, service: Service):
    service.calendar.repository.disconnect(owner)
    return service.calendar.status(owner)
