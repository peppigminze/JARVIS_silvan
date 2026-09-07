def test_create_and_list_task(client, user_headers):
    resp = client.post(
        "/api/tasks",
        json={"title": "Docker-Projekt fertigstellen", "priority": "high"},
        headers=user_headers,
    )
    assert resp.status_code == 200
    task = resp.json()
    assert task["title"] == "Docker-Projekt fertigstellen"
    assert task["status"] == "pending"

    resp = client.get("/api/tasks", headers=user_headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task["id"]


def test_complete_task(client, user_headers):
    created = client.post("/api/tasks", json={"title": "Test"}, headers=user_headers).json()

    resp = client.patch(
        f"/api/tasks/{created['id']}", json={"status": "completed"}, headers=user_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


def test_delete_task(client, user_headers):
    created = client.post("/api/tasks", json={"title": "Test"}, headers=user_headers).json()

    resp = client.delete(f"/api/tasks/{created['id']}", headers=user_headers)
    assert resp.status_code == 200

    resp = client.get("/api/tasks", headers=user_headers)
    assert resp.json() == []


def test_tasks_require_auth(client):
    resp = client.get("/api/tasks")
    assert resp.status_code == 401
