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
