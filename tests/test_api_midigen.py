"""Test MIDI Generator API: generate, batch, save_to_bank, seed determinism."""

import json


def test_info_endpoint_returns_data(client):
    r = client.get("/api/midi_gen/info")
    assert r.status_code == 200
    data = r.json()
    assert "algorithms" in data
    assert "instruments" in data
    assert "scales" in data
    assert "progressions" in data
    assert "defaults" in data
    assert "scale_walk" in data["algorithms"]
    assert len(data["instruments"]) >= 5


def test_generate_basic(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano"}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "filename" in data
    assert data["filename"].endswith(".mid")
    assert isinstance(data["seed"], int)


def test_generate_with_seed(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 42}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.status_code == 200
    data = r.json()
    assert data["seed"] == 42


def test_seed_determinism(client):
    params = {"algorithm": "chord", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 123}
    r1 = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    r2 = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r1.json()["ok"] is True
    assert r2.json()["ok"] is True
    # Same seed → same MIDI content
    import core.config as cfg
    f1 = cfg.OUTPUT_DIR / r1.json()["filename"]
    f2 = cfg.OUTPUT_DIR / r2.json()["filename"]
    assert f1.read_bytes() == f2.read_bytes()


def test_different_seeds_different_output(client):
    params_template = {"algorithm": "scale_walk", "key": "C", "scale": "major",
                       "bpm": 120, "total_bars": 4, "instrument": "piano"}
    p1 = dict(params_template, _seed=100)
    p2 = dict(params_template, _seed=200)
    r1 = client.post("/api/midi_gen/generate", data={"params": json.dumps(p1)})
    r2 = client.post("/api/midi_gen/generate", data={"params": json.dumps(p2)})
    import core.config as cfg
    f1 = cfg.OUTPUT_DIR / r1.json()["filename"]
    f2 = cfg.OUTPUT_DIR / r2.json()["filename"]
    assert f1.read_bytes() != f2.read_bytes()


def test_generate_seed_minus_one(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": -1}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    data = r.json()
    assert data["ok"] is True
    assert data["seed"] is not None
    assert data["seed"] >= 0


def test_generate_with_key_list(client):
    params = {"algorithm": "markov", "key": ["C", "G"], "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano"}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.json()["ok"] is True


def test_generate_with_scale_list(client):
    params = {"algorithm": "chord", "key": "C", "scale": ["major", "minor"],
              "bpm": 120, "total_bars": 4, "instrument": "piano"}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.json()["ok"] is True


def test_all_algorithms_generate(client):
    for algo in ["scale_walk", "chord", "markov", "contour", "combined"]:
        params = {"algorithm": algo, "key": "C", "scale": "major",
                  "bpm": 120, "total_bars": 8, "instrument": "piano", "_seed": 42}
        r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True, f"Algorithm {algo} failed: {data.get('error')}"


def test_generate_invalid_json(client):
    r = client.post("/api/midi_gen/generate", data={"params": "not-json"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False


def test_generate_with_octave_params(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 8, "instrument": "piano",
              "octave_base": 3, "octave_offsets": [1]}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_save_to_bank(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano", "_seed": 1}
    r = client.post("/api/midi_gen/save_to_bank", data={
        "params": json.dumps(params),
        "bank_name": "test_bank",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["bank"] == "test_bank"
    import core.config as cfg
    bank_dir = cfg.MIDI_BANKS / "test_bank"
    assert bank_dir.exists()
    assert len(list(bank_dir.iterdir())) >= 1


def test_generate_batch(client):
    params = {"algorithm": "chord", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano"}
    r = client.post("/api/midi_gen/generate_batch", data={
        "params": json.dumps(params),
        "count": 5,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 5


def test_generate_batch_zero_count(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano"}
    r = client.post("/api/midi_gen/generate_batch", data={
        "params": json.dumps(params),
        "count": 0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 0


def test_generate_empty_instrument(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": ""}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_generate_very_low_octave(client):
    params = {"algorithm": "scale_walk", "key": "C", "scale": "major",
              "bpm": 120, "total_bars": 4, "instrument": "piano",
              "octave_base": 1, "octave_offsets": [-2]}
    r = client.post("/api/midi_gen/generate", data={"params": json.dumps(params)})
    assert r.status_code == 200
    assert r.json()["ok"] is True
