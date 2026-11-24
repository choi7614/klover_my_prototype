"""Calendar 전용 HTTP 경계. 초대·메일·일정 삭제 경로를 제공하지 않는다."""

from urllib.parse import quote

import httpx

from app.schemas.f5 import CalendarConflict
from app.services.calendar import CalendarStoredEvent, CalendarTransportError

SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/calendar.events.owned",
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/calendar.events.freebusy",
    }
)
BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarHTTP:
    mode = "live"

    def __init__(self, access, transport=None):
        self.access, self.transport = access, transport

    def request(self, method, path, *, body=None, params=None, missing=False):
        try:
            with httpx.Client(
                timeout=15, trust_env=False, follow_redirects=False, transport=self.transport
            ) as client:
                response = client.request(
                    method,
                    BASE + path,
                    headers={"Authorization": "Bearer " + self.access},
                    json=body,
                    params=params,
                )
            if missing and response.status_code == 404:
                return None
            kind = {
                400: "rejected",
                401: "auth",
                403: "permission",
                404: "rejected",
                409: "conflict",
                422: "rejected",
            }.get(response.status_code)
            if kind or response.status_code >= 300:
                raise CalendarTransportError(kind or "unavailable")
            if len(response.content) > 1024 * 1024:
                raise ValueError
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError
            return result
        except httpx.TimeoutException:
            raise CalendarTransportError("timeout") from None
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise CalendarTransportError("unavailable") from None

    def calendars(self):
        rows, token = [], None
        for _ in range(20):
            data = self.request(
                "GET",
                "/users/me/calendarList",
                params={"maxResults": 250, **({"pageToken": token} if token else {})},
            )
            for row in data.get("items", []):
                if row.get("accessRole") == "owner" and not row.get("deleted"):
                    rows.append(
                        {
                            "id": row["id"],
                            "label": row.get("summary", row["id"]),
                            "timezone": row.get("timeZone", "UTC"),
                        }
                    )
            token = data.get("nextPageToken")
            if not token:
                return rows
        raise CalendarTransportError("unavailable")

    def find(self, calendar_id, event_id):
        data = self.request(
            "GET",
            "/calendars/" + quote(calendar_id, safe="") + "/events/" + quote(event_id, safe=""),
            missing=True,
        )
        if data is None:
            return None
        return CalendarStoredEvent(
            data.get("id", ""),
            (
                ""
                if data.get("status") == "cancelled"
                else data.get("extendedProperties", {})
                .get("private", {})
                .get("kloverRequestHash", "")
            ),
        )

    def insert(self, request):
        p = request.payload
        data = self.request(
            "POST",
            "/calendars/" + quote(request.calendar_id, safe="") + "/events",
            params={"sendUpdates": "none"},
            body={
                "id": request.event_id,
                "summary": p.title,
                "location": p.location,
                "start": {"dateTime": p.start.isoformat()},
                "end": {"dateTime": p.end.isoformat()},
                "extendedProperties": {"private": {"kloverRequestHash": request.request_hash}},
                "guestsCanInviteOthers": False,
            },
        )
        return CalendarStoredEvent(
            data.get("id", ""),
            (
                ""
                if data.get("status") == "cancelled"
                else data.get("extendedProperties", {})
                .get("private", {})
                .get("kloverRequestHash", "")
            ),
        )

    def freebusy(self, calendar_id, payload):
        data = self.request(
            "POST",
            "/freeBusy",
            body={
                "timeMin": payload.start.isoformat(),
                "timeMax": payload.end.isoformat(),
                "items": [{"id": calendar_id}],
            },
        )
        calendar = data.get("calendars", {}).get(calendar_id)
        if not calendar or calendar.get("errors"):
            raise CalendarTransportError("permission")
        return [CalendarConflict(start=x["start"], end=x["end"]) for x in calendar["busy"]]
