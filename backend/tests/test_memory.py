def test_save_and_search_memory(client, user_headers):
    resp = client.post(
        "/api/memory",
        json={"content": "Mein Minecraft-Projekt heißt AlwaysMC.", "category": "projects"},
        headers=user_headers,
    )
    assert resp.status_code == 200

    resp = client.get("/api/memory", params={"q": "Minecraft"}, headers=user_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "AlwaysMC" in results[0]["content"]


def test_list_all_memory(client, user_headers):
    client.post("/api/memory", json={"content": "Fakt A"}, headers=user_headers)
    client.post("/api/memory", json={"content": "Fakt B"}, headers=user_headers)

    resp = client.get("/api/memory", headers=user_headers)
    assert len(resp.json()) == 2


def test_memory_defaults_to_fact_type(client, user_headers):
    resp = client.post("/api/memory", json={"content": "Ohne Typ angegeben"}, headers=user_headers)
    assert resp.json()["memory_type"] == "fact"


def test_memory_type_is_validated(client, user_headers):
    resp = client.post(
        "/api/memory", json={"content": "x", "memory_type": "not-a-real-type"}, headers=user_headers
    )
    assert resp.status_code == 422


def test_memory_can_be_saved_as_preference_and_filtered(client, user_headers):
    client.post(
        "/api/memory",
        json={"content": "Antworte immer auf Deutsch.", "memory_type": "preference"},
        headers=user_headers,
    )
    client.post("/api/memory", json={"content": "Ein Fakt."}, headers=user_headers)

    resp = client.get("/api/memory", params={"memory_type": "preference"}, headers=user_headers)
    results = resp.json()
    assert len(results) == 1
    assert results[0]["memory_type"] == "preference"


def test_delete_memory(client, user_headers):
    created = client.post("/api/memory", json={"content": "Löschbar"}, headers=user_headers).json()

    resp = client.delete(f"/api/memory/{created['id']}", headers=user_headers)
    assert resp.status_code == 200

    resp = client.get("/api/memory", headers=user_headers)
    assert resp.json() == []


def test_delete_memory_not_found(client, user_headers):
    resp = client.delete("/api/memory/999999", headers=user_headers)
    assert resp.status_code == 404
