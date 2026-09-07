def _create_pending_action(client, agent_headers, message_id=None, tool_name="delete_task"):
    resp = client.post(
        "/api/sync/actions",
        json={
            "message_id": message_id,
            "tool_name": tool_name,
            "arguments": {"task_id": 1},
            "observations": [],
            "reply": "Soll ich Task 1 löschen?",
        },
        headers=agent_headers,
    )
    assert resp.status_code == 200
    return resp.json()


def test_agent_creates_pending_action_and_it_is_listed_for_the_user(client, agent_headers, user_headers):
    action = _create_pending_action(client, agent_headers)
    assert action["status"] == "awaiting_confirmation"

    listed = client.get("/api/actions", headers=user_headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == action["id"]
    assert listed[0]["tool_name"] == "delete_task"


def test_user_confirms_action(client, agent_headers, user_headers):
    action = _create_pending_action(client, agent_headers)

    resp = client.post(f"/api/actions/{action['id']}/confirm", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # No longer listed under the default (awaiting_confirmation) filter.
    listed = client.get("/api/actions", headers=user_headers).json()
    assert listed == []


def test_user_rejects_action_and_message_is_completed_with_a_note(client, agent_headers, user_headers):
    created = client.post("/api/messages", json={"content": "Lösch Task 1"}, headers=user_headers).json()
    client.get("/api/sync/pending", headers=agent_headers)  # claim -> processing

    action = _create_pending_action(client, agent_headers, message_id=created["id"])

    resp = client.post(f"/api/actions/{action['id']}/reject", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    message = client.get("/api/messages", headers=user_headers).json()[-1]
    assert message["status"] == "completed"
    assert "nicht ausgeführt" in message["response"]


def test_cannot_confirm_an_already_resolved_action(client, agent_headers, user_headers):
    action = _create_pending_action(client, agent_headers)
    client.post(f"/api/actions/{action['id']}/confirm", headers=user_headers)

    resp = client.post(f"/api/actions/{action['id']}/confirm", headers=user_headers)
    assert resp.status_code == 409


def test_agent_claims_confirmed_actions_exactly_once(client, agent_headers, user_headers):
    action = _create_pending_action(client, agent_headers)
    client.post(f"/api/actions/{action['id']}/confirm", headers=user_headers)

    first_claim = client.get("/api/sync/confirmed-actions", headers=agent_headers).json()
    assert len(first_claim) == 1
    assert first_claim[0]["status"] == "executing"

    second_claim = client.get("/api/sync/confirmed-actions", headers=agent_headers).json()
    assert second_claim == []


def test_agent_completes_a_claimed_action(client, agent_headers, user_headers):
    action = _create_pending_action(client, agent_headers)
    client.post(f"/api/actions/{action['id']}/confirm", headers=user_headers)
    client.get("/api/sync/confirmed-actions", headers=agent_headers)

    resp = client.post(
        f"/api/sync/actions/{action['id']}/complete",
        json={"result": {"deleted": True}},
        headers=agent_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["result"] == {"deleted": True}


def test_actions_require_correct_token(client, agent_headers, user_headers):
    action = _create_pending_action(client, agent_headers)

    # Agent token must not be able to confirm (that's a human-only action).
    resp = client.post(f"/api/actions/{action['id']}/confirm", headers=agent_headers)
    assert resp.status_code == 401

    # User token must not be able to claim confirmed actions.
    resp = client.get("/api/sync/confirmed-actions", headers=user_headers)
    assert resp.status_code == 401
