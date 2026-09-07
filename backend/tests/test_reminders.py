from datetime import datetime, timedelta, timezone


def test_create_task_with_reminder_and_tags(client, user_headers):
    due = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    resp = client.post(
        "/api/tasks",
        json={
            "title": "Zahnarzttermin",
            "due_at": due,
            "reminder_enabled": True,
            "recurrence": "none",
            "tags": ["gesundheit", "wichtig"],
            "notes": "Anrufen falls Verschiebung nötig",
        },
        headers=user_headers,
    )
    assert resp.status_code == 200
    task = resp.json()
    assert task["reminder_enabled"] is True
    assert task["tags"] == ["gesundheit", "wichtig"]
    assert task["notes"] == "Anrufen falls Verschiebung nötig"


def test_reminder_without_due_at_is_not_enabled(client, user_headers):
    resp = client.post(
        "/api/tasks", json={"title": "Kein Datum", "reminder_enabled": True}, headers=user_headers
    )
    assert resp.json()["reminder_enabled"] is False


def test_invalid_recurrence_is_rejected(client, user_headers):
    resp = client.post(
        "/api/tasks",
        json={"title": "x", "due_at": datetime.now(timezone.utc).isoformat(), "recurrence": "hourly"},
        headers=user_headers,
    )
    assert resp.status_code == 422


def test_due_reminders_endpoint_is_empty_before_scheduler_runs(client, user_headers):
    due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    client.post(
        "/api/tasks",
        json={"title": "Fällig", "due_at": due, "reminder_enabled": True},
        headers=user_headers,
    )
    resp = client.get("/api/tasks/due-reminders", headers=user_headers)
    assert resp.json() == []  # scheduler hasn't ticked yet - see test_scheduler.py for that


def test_due_reminders_requires_auth(client):
    resp = client.get("/api/tasks/due-reminders")
    assert resp.status_code == 401
