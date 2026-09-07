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
