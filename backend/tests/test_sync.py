def test_sync_pending_flow(client, user_headers, agent_headers):
    client.post("/api/messages", json={"content": "Öffne IntelliJ"}, headers=user_headers)

    pending = client.get("/api/sync/pending", headers=agent_headers).json()
    assert len(pending) == 1
    assert pending[0]["status"] == "processing"

    complete = client.post(
        "/api/sync/complete",
        json={"message_id": pending[0]["id"], "response": "Erledigt."},
        headers=agent_headers,
    ).json()
    assert complete["status"] == "completed"
    assert complete["response"] == "Erledigt."


def test_sync_fail_flow(client, user_headers, agent_headers):
    client.post("/api/messages", json={"content": "Etwas Kaputtes"}, headers=user_headers)
    pending = client.get("/api/sync/pending", headers=agent_headers).json()

    failed = client.post(
        "/api/sync/fail",
        json={"message_id": pending[0]["id"], "error": "Tool nicht gefunden."},
        headers=agent_headers,
    ).json()
    assert failed["status"] == "failed"
    assert failed["error"] == "Tool nicht gefunden."


def test_pending_prevents_double_processing(client, user_headers, agent_headers):
    """Once claimed (status flips to 'processing'), a message must not be
    returned again by a second poll before it's completed/failed."""
    client.post("/api/messages", json={"content": "Nur einmal verarbeiten"}, headers=user_headers)

    first_poll = client.get("/api/sync/pending", headers=agent_headers).json()
    assert len(first_poll) == 1

    second_poll = client.get("/api/sync/pending", headers=agent_headers).json()
    assert len(second_poll) == 0


def test_sync_requires_agent_token(client, user_headers):
    resp = client.get("/api/sync/pending", headers=user_headers)
    assert resp.status_code == 401


def test_retry_requeues_message_and_hides_it_until_next_retry_at(client, user_headers, agent_headers):
    from datetime import datetime, timedelta, timezone

    client.post("/api/messages", json={"content": "Retry mich"}, headers=user_headers)
    pending = client.get("/api/sync/pending", headers=agent_headers).json()
    message_id = pending[0]["id"]

    future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    retried = client.post(
        "/api/sync/retry",
        json={"message_id": message_id, "retry_count": 1, "next_retry_at": future, "error": "LLM down"},
        headers=agent_headers,
    ).json()
    assert retried["status"] == "pending"
    assert retried["retry_count"] == 1

    # Not due yet - must not be claimed again.
    second_poll = client.get("/api/sync/pending", headers=agent_headers).json()
    assert second_poll == []


def test_retry_message_becomes_claimable_once_next_retry_at_has_passed(client, user_headers, agent_headers):
    from datetime import datetime, timedelta, timezone

    client.post("/api/messages", json={"content": "Retry mich bald"}, headers=user_headers)
    pending = client.get("/api/sync/pending", headers=agent_headers).json()
    message_id = pending[0]["id"]

    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    client.post(
        "/api/sync/retry",
        json={"message_id": message_id, "retry_count": 1, "next_retry_at": past, "error": "LLM down"},
        headers=agent_headers,
    )

    second_poll = client.get("/api/sync/pending", headers=agent_headers).json()
    assert len(second_poll) == 1
    assert second_poll[0]["id"] == message_id


def test_retry_requires_agent_token(client, user_headers):
    resp = client.post(
        "/api/sync/retry",
        json={"message_id": 1, "retry_count": 1, "next_retry_at": None},
        headers=user_headers,
    )
    assert resp.status_code == 401
