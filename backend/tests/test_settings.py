def test_settings_requires_auth(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 401


def test_settings_overview(client, user_headers):
    resp = client.get("/api/settings", headers=user_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "local"
    assert "wake_on_lan" in body
    assert isinstance(body["allowed_directories"], list)


def test_wake_on_lan_unconfigured_by_default(client, user_headers, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("WAKE_ON_LAN_MAC", "")
    get_settings.cache_clear()
    try:
        resp = client.get("/api/settings", headers=user_headers)
        wol = resp.json()["wake_on_lan"]
        assert wol["configured"] is False
        assert wol["mac_address"] is None
        assert wol["command"] is None
    finally:
        get_settings.cache_clear()


def test_wake_on_lan_configured(client, user_headers, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("WAKE_ON_LAN_MAC", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setenv("WAKE_ON_LAN_BROADCAST", "192.168.1.255")
    get_settings.cache_clear()
    try:
        resp = client.get("/api/settings", headers=user_headers)
        wol = resp.json()["wake_on_lan"]
        assert wol["configured"] is True
        assert wol["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert "192.168.1.255" in wol["command"]
    finally:
        get_settings.cache_clear()


def test_cloud_llm_model_hidden_when_disabled(client, user_headers, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("CLOUD_LLM_ENABLED", "false")
    get_settings.cache_clear()
    try:
        resp = client.get("/api/settings", headers=user_headers)
        assert resp.json()["cloud_llm_model"] is None
    finally:
        get_settings.cache_clear()
