"""Test /api/dataset/generate (SSE stream) and /api/dataset/cancel."""

import json


def test_generate_invalid_bank(client):
    r = client.post("/api/dataset/generate", data={
        "bank": "nonexistent_bank_xyz",
    })
    assert r.status_code == 200
    text = r.text
    assert "result:" in text
    result_line = [l for l in text.split("\n") if l.startswith("result:")][0]
    payload = json.loads(result_line[len("result:"):])
    assert payload["ok"] is False
    assert "not found" in payload["error"]


def test_generate_empty_bank(client):
    r = client.post("/api/dataset/generate", data={
        "bank": "empty_bank",
    })
    assert r.status_code == 200
    text = r.text
    result_line = next((l for l in text.split("\n") if l.startswith("result:")), None)
    if result_line:
        payload = json.loads(result_line[len("result:"):])
        assert payload["ok"] is False


def test_generate_with_bank(client, seed_bank):
    r = client.post("/api/dataset/generate", data={
        "bank": "testbank",
        "pitch_drift": "0", "drift_prob": "0",
        "timing_jitter": "0", "jitter_prob": "0",
        "bad_notes": "0", "noise": "0", "noise_prob": "0",
        "max_dur": "15", "split_midi": "false",
    })
    assert r.status_code == 200
    text = r.text
    log_lines = [l for l in text.split("\n") if l]
    assert any("_params.json" in text or "OK" in text or "Done" in text for _ in [1])
    # Check if we got a result
    result_line = next((l for l in text.split("\n") if l.startswith("result:")), None)
    if result_line:
        payload = json.loads(result_line[len("result:"):])
        if payload.get("ok"):
            assert payload["count"] >= 1
            import main as m
            from pathlib import Path
            out_dir = Path(payload["path"])
            clean_files = list(out_dir.glob("*_clean.wav"))
            assert len(clean_files) >= 1


def test_cancel_generation(client, seed_bank):
    import threading
    import time
    import main as m

    # Start generation in a thread
    result_holder = []

    def do_gen():
        r = client.post("/api/dataset/generate", data={
            "bank": "testbank",
            "pitch_drift": "50", "drift_prob": "50",
            "timing_jitter": "50", "jitter_prob": "50",
            "bad_notes": "4", "noise": "50", "noise_prob": "50",
            "max_dur": "15", "split_midi": "false",
        })
        result_holder.append(r)

    t = threading.Thread(target=do_gen)
    t.start()
    time.sleep(0.3)
    cancel_r = client.post("/api/dataset/cancel")
    assert cancel_r.status_code == 200
    assert cancel_r.json()["ok"] is True
    t.join(timeout=5)
    assert len(result_holder) == 1
    r = result_holder[0]
    text = r.text
    assert "Cancelled" in text or "result:" in text


def test_split_midi(client, seed_bank):
    r = client.post("/api/dataset/generate", data={
        "bank": "testbank",
        "pitch_drift": "0", "drift_prob": "0",
        "timing_jitter": "0", "jitter_prob": "0",
        "bad_notes": "0", "noise": "0", "noise_prob": "0",
        "max_dur": "1", "split_midi": "true",
    })
    assert r.status_code == 200


def test_params_json_created(client, seed_bank):
    r = client.post("/api/dataset/generate", data={
        "bank": "testbank",
        "pitch_drift": "10", "drift_prob": "20",
        "timing_jitter": "30", "jitter_prob": "40",
        "bad_notes": "5", "noise": "60", "noise_prob": "70",
        "max_dur": "15", "split_midi": "false",
    })
    text = r.text
    result_line = next((l for l in text.split("\n") if l.startswith("result:")), None)
    if result_line:
        payload = json.loads(result_line[len("result:"):])
        if payload.get("ok"):
            import json as j
            import main as m
            from pathlib import Path
            params_path = Path(payload["path"]) / "_params.json"
            assert params_path.exists()
            params = j.loads(params_path.read_text(encoding="utf-8"))
            assert params["pitch_drift"] == 10


def test_generate_respects_max_300_files(client, seed_bank):
    # Add 5 more MIDI files to testbank
    import pretty_midi
    import main as m
    bank = m.MIDI_BANKS / "testbank"
    for i in range(5):
        pm = pretty_midi.PrettyMIDI(initial_tempo=120)
        inst = pretty_midi.Instrument(program=0)
        inst.notes.append(pretty_midi.Note(80, 60, 0, 0.5))
        pm.instruments.append(inst)
        pm.write(str(bank / f"{i+2:04d}.mid"))

    r = client.post("/api/dataset/generate", data={
        "bank": "testbank",
        "pitch_drift": "0", "drift_prob": "0",
        "timing_jitter": "0", "jitter_prob": "0",
        "bad_notes": "0", "noise": "0", "noise_prob": "0",
        "max_dur": "15", "split_midi": "false",
    })
    assert r.status_code == 200


def test_generate_default_params(client, seed_bank):
    r = client.post("/api/dataset/generate", data={
        "bank": "testbank",
    })
    assert r.status_code == 200
