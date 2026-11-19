import pytest

from app.schemas.f5 import ApproveRequest
from app.services.f5_errors import F5Error

from .helpers import OTHER, OWNER, TOKEN, client, headers


def test_api_auth_origin_query_and_input_rejection(f5db):
    rows = f5db.service.scan(OWNER, f5db.analysis).items
    with client(f5db.service) as http:
        for path in ["/suggestions", "/todos", "/suggestion-events"]:
            assert http.get(path).status_code == 401
            for extra in [
                {"Origin": "null"},
                {"Host": "foreign.invalid"},
                {"X-Forwarded-For": "127.0.0.1"},
            ]:
                response = http.get(path, headers=headers() | extra)
                assert (
                    response.status_code == 403 and response.headers["cache-control"] == "no-store"
                )
        for path in [
            "/suggestions?user_id=other",
            "/suggestions?limit=1&limit=2",
            "/todos?account_id=other",
            "/suggestion-events?limit=101",
        ]:
            response = http.get(path, headers=headers())
            assert response.status_code == 422
            assert TOKEN not in response.text
        row = rows[0]
        response = http.post(
            f"/suggestions/{row.suggestion_id}/approve",
            headers=headers(),
            json={"version": 1, "user_id": "other"},
        )
        assert response.status_code == 422
        assert http.patch("/todos/none", headers=headers(), json={"version": 1}).status_code == 422
        assert http.post("/suggestions", headers=headers(), json={}).status_code == 405


def test_api_state_todos_missed_and_ack(f5db):
    rows = f5db.service.scan(OWNER, f5db.analysis).items
    with client(f5db.service) as http:
        assert (
            len(
                http.get("/suggestions?status=pending&notified=false", headers=headers()).json()[
                    "items"
                ]
            )
            == 3
        )
        calendar = rows[0]
        response = http.post(
            f"/suggestions/{calendar.suggestion_id}/approve", headers=headers(), json={"version": 1}
        )
        assert response.status_code == 200
        assert (
            response.json()["status"] == "pending"
            and response.json()["execution_status"] == "simulated"
        )
        event = http.get("/suggestion-events", headers=headers()).json()["items"][0]
        assert (
            http.post(f"/suggestion-events/{event['event_id']}/ack", headers=headers()).status_code
            == 204
        )
        assert (
            len(
                http.get("/suggestions?status=pending&notified=false", headers=headers()).json()[
                    "items"
                ]
            )
            == 2
        )
        todo = rows[1]
        response = http.post(
            f"/suggestions/{todo.suggestion_id}/approve", headers=headers(), json={"version": 1}
        )
        assert response.json()["status"] == "approved"
        saved = http.get("/todos", headers=headers()).json()["items"][0]
        assert saved["suggestion_id"] == todo.suggestion_id
        assert (
            http.patch(
                f"/todos/{saved['todo_id']}",
                headers=headers(),
                json={"version": 1, "status": "completed"},
            ).status_code
            == 200
        )
        reply = rows[2]
        assert (
            http.post(
                f"/suggestions/{reply.suggestion_id}/dismiss",
                headers=headers(),
                json={"version": 1},
            ).json()["status"]
            == "dismissed"
        )


def test_foreign_user_cannot_read_approve_dismiss_or_ack(f5db):
    rows = f5db.service.scan(OWNER, f5db.analysis).items
    event = f5db.repository.events(OWNER).items[0]
    with client(f5db.service, owner=OTHER) as http:
        assert http.get("/suggestions", headers=headers()).json()["items"] == []
        for method, path, body in [
            ("get", f"/suggestions/{rows[0].suggestion_id}", None),
            ("post", f"/suggestions/{rows[0].suggestion_id}/approve", {"version": 1}),
            ("post", f"/suggestions/{rows[0].suggestion_id}/dismiss", {"version": 1}),
            ("post", f"/suggestion-events/{event.event_id}/ack", None),
        ]:
            args = {"headers": headers()}
            if body:
                args["json"] = body
            response = getattr(http, method)(path, **args)
            assert response.status_code == 404
    assert f5db.transport.writes == []


def test_failed_approval_is_not_success_and_errors_do_not_leak(f5db, caplog):
    row = f5db.service.scan(OWNER, f5db.analysis).items[0]

    def broken(*args):
        raise RuntimeError("synthetic-private-mail-token")

    f5db.service.calendar.execute = broken
    with client(f5db.service) as http:
        response = http.post(
            f"/suggestions/{row.suggestion_id}/approve", headers=headers(), json={"version": 1}
        )
        assert response.status_code == 502
        current = http.get(f"/suggestions/{row.suggestion_id}", headers=headers()).json()
        assert current["status"] == "pending" and current["execution_status"] == "uncertain"
        assert current["result"] is None
        assert "synthetic-private" not in response.text + caplog.text
    with pytest.raises(F5Error, match="not_found"):
        f5db.service.approve(OTHER, row.suggestion_id, ApproveRequest(version=1))
