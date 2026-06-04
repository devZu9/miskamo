"""Test MIDI banks API: list, rename, delete."""


def test_banks_list_empty(client):
    r = client.get("/api/banks")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["banks"] == []


def test_banks_list_with_bank(client, seed_bank):
    r = client.get("/api/banks")
    data = r.json()
    names = [b["name"] for b in data["banks"]]
    assert "testbank" in names


def test_bank_rename(client, seed_bank):
    r = client.post("/api/banks/rename", data={
        "old_name": "testbank",
        "new_name": "renamed_bank",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["name"] == "renamed_bank"
    # Verify rename
    import main as m
    assert (m.MIDI_BANKS / "renamed_bank").exists()
    assert not (m.MIDI_BANKS / "testbank").exists()


def test_bank_rename_nonexistent(client):
    r = client.post("/api/banks/rename", data={
        "old_name": "no_such_bank",
        "new_name": "new_name",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["error"] == "not found"


def test_bank_rename_to_existing(client, seed_bank):
    import main as m
    other = m.MIDI_BANKS / "other_bank"
    other.mkdir()
    (other / "dummy.mid").write_text("")
    r = client.post("/api/banks/rename", data={
        "old_name": "testbank",
        "new_name": "other_bank",
    })
    assert r.json()["ok"] is False
    assert r.json()["error"] == "exists"


def test_bank_delete(client, seed_bank):
    r = client.post("/api/banks/delete", data={"name": "testbank"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    import main as m
    assert not (m.MIDI_BANKS / "testbank").exists()


def test_bank_delete_nonexistent(client):
    r = client.post("/api/banks/delete", data={"name": "no_such_bank"})
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["error"] == "not found"


def test_save_bank(client):
    r = client.post("/api/save_bank", data={"midi_bank": "some_bank"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_bank_rename_cyrillic(client, seed_bank):
    r = client.post("/api/banks/rename", data={
        "old_name": "testbank",
        "new_name": "Новая Банка",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    # Should be transliterated
    import main as m
    assert not (m.MIDI_BANKS / "testbank").exists()
    # Find the renamed dir
    dirs = [d.name for d in m.MIDI_BANKS.iterdir() if d.is_dir()]
    assert any("novaya" in d.lower() for d in dirs) or any("bank" in d.lower() for d in dirs)
