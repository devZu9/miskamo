"""Test MIDI Gen presets CRUD."""

import json


def test_list_empty(client):
    r = client.get("/api/midi_gen/presets")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["presets"] == []


def test_create_preset(client):
    params = {"algorithm": "scale_walk", "key": ["C"], "scale": ["major"],
              "bpm": 120, "total_bars": 8, "instrument": "piano"}
    r = client.post("/api/midi_gen/presets/save", data={
        "name": "Test Preset",
        "params": json.dumps(params),
        "overwrite": "false",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_create_and_list(client):
    params = {"algorithm": "chord", "key": ["G"], "time_signature": "3/4"}
    client.post("/api/midi_gen/presets/save", data={
        "name": "My Preset",
        "params": json.dumps(params),
        "overwrite": "false",
    })
    r = client.get("/api/midi_gen/presets")
    names = [p["name"] for p in r.json()["presets"]]
    assert "My Preset" in names


def test_create_duplicate_fails(client):
    params = json.dumps({"algorithm": "markov"})
    client.post("/api/midi_gen/presets/save", data={
        "name": "Dup", "params": params, "overwrite": "false",
    })
    r = client.post("/api/midi_gen/presets/save", data={
        "name": "Dup", "params": params, "overwrite": "false",
    })
    data = r.json()
    assert data["ok"] is False
    assert data["error"] == "exists"


def test_create_duplicate_overwrite(client):
    params1 = json.dumps({"algorithm": "chord", "bpm": 100})
    params2 = json.dumps({"algorithm": "contour", "bpm": 200})
    client.post("/api/midi_gen/presets/save", data={
        "name": "OverwriteMe", "params": params1, "overwrite": "false",
    })
    r = client.post("/api/midi_gen/presets/save", data={
        "name": "OverwriteMe", "params": params2, "overwrite": "true",
    })
    assert r.json()["ok"] is True
    # Verify the preset was updated
    r2 = client.get("/api/midi_gen/presets/load?name=OverwriteMe")
    assert r2.json()["data"]["algorithm"] == "contour"


def test_load_preset(client):
    params = {"algorithm": "contour", "climax_bar": 3, "instrument": "flute"}
    client.post("/api/midi_gen/presets/save", data={
        "name": "LoadMe",
        "params": json.dumps(params),
        "overwrite": "false",
    })
    r = client.get("/api/midi_gen/presets/load?name=LoadMe")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["data"]["algorithm"] == "contour"
    assert data["data"]["climax_bar"] == 3


def test_load_nonexistent(client):
    r = client.get("/api/midi_gen/presets/load?name=Nobody")
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_delete_preset(client):
    params = json.dumps({"algorithm": "scale_walk"})
    client.post("/api/midi_gen/presets/save", data={
        "name": "DeleteMe", "params": params, "overwrite": "false",
    })
    r = client.post("/api/midi_gen/presets/delete", data={"name": "DeleteMe"})
    assert r.json()["ok"] is True
    r2 = client.get("/api/midi_gen/presets/load?name=DeleteMe")
    assert r2.json()["ok"] is False


def test_delete_nonexistent(client):
    r = client.post("/api/midi_gen/presets/delete", data={"name": "Noone"})
    assert r.json()["ok"] is True


def test_rename_preset(client):
    params = json.dumps({"algorithm": "markov"})
    client.post("/api/midi_gen/presets/save", data={
        "name": "OldName", "params": params, "overwrite": "false",
    })
    r = client.post("/api/midi_gen/presets/rename", data={
        "old_name": "OldName", "new_name": "NewName", "overwrite": "false",
    })
    assert r.json()["ok"] is True
    r1 = client.get("/api/midi_gen/presets/load?name=OldName")
    assert r1.json()["ok"] is False
    r2 = client.get("/api/midi_gen/presets/load?name=NewName")
    assert r2.json()["ok"] is True


def test_rename_nonexistent(client):
    r = client.post("/api/midi_gen/presets/rename", data={
        "old_name": "Noone", "new_name": "New", "overwrite": "false",
    })
    assert r.json()["ok"] is False
    assert r.json()["error"] == "not found"


def test_rename_to_existing_no_overwrite(client):
    p = json.dumps({"algorithm": "scale_walk"})
    client.post("/api/midi_gen/presets/save", data={"name": "A", "params": p, "overwrite": "false"})
    client.post("/api/midi_gen/presets/save", data={"name": "B", "params": p, "overwrite": "false"})
    r = client.post("/api/midi_gen/presets/rename", data={
        "old_name": "A", "new_name": "B", "overwrite": "false",
    })
    assert r.json()["ok"] is False
    assert r.json()["error"] == "exists"


def test_rename_to_existing_with_overwrite(client):
    pa = json.dumps({"algorithm": "scale_walk", "bpm": 100})
    pb = json.dumps({"algorithm": "chord", "bpm": 200})
    client.post("/api/midi_gen/presets/save", data={"name": "A", "params": pa, "overwrite": "false"})
    client.post("/api/midi_gen/presets/save", data={"name": "B", "params": pb, "overwrite": "false"})
    r = client.post("/api/midi_gen/presets/rename", data={
        "old_name": "A", "new_name": "B", "overwrite": "true",
    })
    assert r.json()["ok"] is True
    r2 = client.get("/api/midi_gen/presets/load?name=B")
    assert r2.json()["data"]["algorithm"] == "scale_walk"


def test_preset_has_name_in_data(client):
    params = {"algorithm": "scale_walk", "instrument": "sax"}
    client.post("/api/midi_gen/presets/save", data={
        "name": "Named Preset",
        "params": json.dumps(params),
        "overwrite": "false",
    })
    r = client.get("/api/midi_gen/presets/load?name=Named Preset")
    assert r.json()["data"]["_name"] == "Named Preset"


def test_invalid_params_json(client):
    r = client.post("/api/midi_gen/presets/save", data={
        "name": "Bad",
        "params": "not-json",
        "overwrite": "false",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_cyrillic_preset_name(client):
    params = json.dumps({"algorithm": "markov"})
    r = client.post("/api/midi_gen/presets/save", data={
        "name": "Тестовый пресет",
        "params": params,
        "overwrite": "false",
    })
    assert r.json()["ok"] is True
    r2 = client.get("/api/midi_gen/presets/load?name=Тестовый пресет")
    assert r2.json()["ok"] is True
