"""Workflow tests: generate → pianoroll → render → save."""
import json


def test_generate_returns_pianoroll_params(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 8, "instrument": "piano", "_seed": 1,
              "note_range_low": 48, "note_range_high": 84}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    data = r.json()
    assert data["ok"]
    assert "pitch_low" in data
    assert "pitch_high" in data
    assert data["total_bars"] == 8


def test_generate_then_pianoroll_serves_image(client):
    params = {"algorithm": "chord", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 42}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    filename = r.json()["filename"]
    r2 = client.get(f"/api/midi/pianoroll?file={filename}")
    assert r2.status_code == 200
    assert r2.headers["content-type"] in ("image/png", "application/octet-stream")
    body = r2.read()
    assert len(body) > 100
    assert body[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_then_render_serves_audio(client):
    params = {"algorithm": "markov", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 7}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    filename = r.json()["filename"]
    r2 = client.get(f"/api/midi/render?file={filename}")
    assert r2.status_code == 200
    body = r2.read()
    assert len(body) > 100


def test_generate_then_save_to_bank_and_list(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 99}
    r = client.post("/api/midi_gen/save_to_bank", data={
        "params": json.dumps(params), "bank_name": "workflow_bank",
    })
    assert r.json()["ok"]
    import core.config as cfg
    bank_dir = cfg.MIDI_BANKS / "workflow_bank"
    assert bank_dir.exists()
    midis = list(bank_dir.glob("*.mid*"))
    assert len(midis) >= 1

    r2 = client.get("/api/banks")
    banks = r2.json()
    names = [b["name"] for b in banks.get("banks", [])]
    assert "workflow_bank" in names


def test_generate_invalid_key_fallback(client):
    params = {"algorithm": "scale_walk", "key": "D", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 1}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.json()["ok"]


def test_generate_invalid_scale_defaults(client):
    params = {"algorithm": "chord", "key": "C", "scale": "invalid",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 1}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.json()["ok"]


def test_generate_batch_with_different_params(client):
    params = {"algorithm": "scale_walk", "key": ["C", "G"], "scale": ["major", "minor"],
              "bpm": 120, "total_bars": 4, "instrument": "piano"}
    r = client.post("/api/midi_gen/generate_batch", data={
        "params": json.dumps(params), "count": 4,
    })
    data = r.json()
    assert data["ok"]
    assert data["count"] == 4


def test_save_preset_then_load(client):
    params = json.dumps({"algorithm": "scale_walk", "bpm": 140, "instrument": "guitar"})
    r = client.post("/api/midi_gen/presets/save", data={
        "name": "Workflow Preset", "params": params, "overwrite": "false",
    })
    assert r.json()["ok"]
    r2 = client.get("/api/midi_gen/presets/load?name=Workflow Preset")
    assert r2.json()["data"]["bpm"] == 140
    assert r2.json()["data"]["instrument"] == "guitar"


def test_load_preset_then_generate(client):
    params = json.dumps({"algorithm": "chord", "bpm": 160, "instrument": "flute",
                         "key": "D", "scale": "blues", "_seed": 42})
    client.post("/api/midi_gen/presets/save", data={
        "name": "GenFromPreset", "params": params, "overwrite": "false",
    })
    r = client.get("/api/midi_gen/presets/load?name=GenFromPreset")
    preset = r.json()["data"]
    gen_params = {k: v for k, v in preset.items() if k != "_name"}
    r2 = client.post("/api/midi_gen/generate", data={"params": json.dumps(gen_params)})
    assert r2.json()["ok"]


def test_generate_with_pianoroll_custom_params(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 8, "instrument": "piano", "_seed": 1,
              "note_range_low": 48, "note_range_high": 84}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    data = r.json()
    if data.get("pitch_low") is not None:
        r2 = client.get(f"/api/midi/pianoroll?file={data['filename']}"
                        f"&pitch_low={data['pitch_low']}&pitch_high={data['pitch_high']}"
                        f"&total_bars={data['total_bars']}")
        assert r2.status_code == 200
        body = r2.read()
        assert body[:8] == b"\x89PNG\r\n\x1a\n"


def test_delete_preset_then_load_fails(client):
    params = json.dumps({"algorithm": "markov"})
    client.post("/api/midi_gen/presets/save", data={
        "name": "ToDelete", "params": params, "overwrite": "false",
    })
    r = client.post("/api/midi_gen/presets/delete", data={"name": "ToDelete"})
    assert r.json()["ok"]
    r2 = client.get("/api/midi_gen/presets/load?name=ToDelete")
    assert not r2.json()["ok"]


def test_rename_preset_then_load_by_new_name(client):
    p = json.dumps({"algorithm": "contour", "climax_bar": 6})
    client.post("/api/midi_gen/presets/save", data={
        "name": "RenameMe", "params": p, "overwrite": "false",
    })
    r = client.post("/api/midi_gen/presets/rename", data={
        "old_name": "RenameMe", "new_name": "Renamed", "overwrite": "false",
    })
    assert r.json()["ok"]
    r2 = client.get("/api/midi_gen/presets/load?name=Renamed")
    assert r2.json()["data"]["climax_bar"] == 6
