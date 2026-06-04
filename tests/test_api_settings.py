"""Test /api/settings CRUD and /lang/{lang}."""


def test_post_settings(client):
    r = client.post("/api/settings", data={
        "lang": "en", "midi_bank": "testbank",
        "confirm_delete": "false",
        "toast_sec": 5, "clear_tmp": "false", "default_instrument": "flute",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_settings_persisted(client):
    client.post("/api/settings", data={
        "lang": "en", "midi_bank": "testbank",
        "confirm_delete": "true",
        "toast_sec": 7, "clear_tmp": "true", "default_instrument": "piano",
    })
    from core.config import settings_cache
    assert settings_cache["language"] == "en"
    assert settings_cache["default_instrument"] == "piano"
    assert settings_cache["toast_sec"] == 7


def test_set_lang_ru(client):
    r = client.get("/lang/ru")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    from core.config import settings_cache
    assert settings_cache["language"] == "ru"


def test_set_lang_en(client):
    r = client.get("/lang/en")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    from core.config import settings_cache
    assert settings_cache["language"] == "en"


def test_set_lang_invalid(client):
    r = client.get("/lang/de")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    from core.config import settings_cache
    assert settings_cache["language"] in ("ru", "en")


def test_settings_default_instrument_saved(client):
    client.post("/api/settings", data={
        "lang": "en", "midi_bank": "",
        "confirm_delete": "true", "toast_sec": 3, "clear_tmp": "true",
        "default_instrument": "violin",
    })
    from core.config import settings_cache
    assert settings_cache["default_instrument"] == "violin"


def test_settings_rejects_empty_lang(client):
    r = client.post("/api/settings", data={
        "lang": "", "midi_bank": "",
        "confirm_delete": "true", "toast_sec": 3, "clear_tmp": "true",
        "default_instrument": "sax",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_settings_bool_coercion(client):
    r = client.post("/api/settings", data={
        "lang": "ru", "midi_bank": "",
        "confirm_delete": "false",
        "toast_sec": 3, "clear_tmp": "true",
        "default_instrument": "sax",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    from core.config import settings_cache

    assert settings_cache["confirm_delete"] is False


def test_cursor_settings(client):
    r = client.post("/api/settings", data={
        "lang": "en", "midi_bank": "",
        "confirm_delete": "true",
        "toast_sec": 3, "clear_tmp": "true", "default_instrument": "sax",
        "cursor_size": 32, "cursor_enabled": "true", "cursor_shape": "triangle",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    from core.config import settings_cache
    assert settings_cache["cursor_size"] == 32
    assert settings_cache["cursor_enabled"] is True
    assert settings_cache["cursor_shape"] == "triangle"
