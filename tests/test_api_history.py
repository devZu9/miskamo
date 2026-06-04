"""Test /api/history: list, delete, clear."""


def test_history_empty(client):
    r = client.get("/api/history")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["entries"] == []
    assert data["total"] == 0


def test_history_with_files(client, seed_midi, seed_wav):
    r = client.get("/api/history")
    data = r.json()
    assert len(data["entries"]) >= 1
    entry = data["entries"][0]
    assert "uid" in entry
    assert "ts" in entry
    assert "audio" in entry
    assert "midi" in entry


def test_history_pagination(client):
    # Create 30 entries (60 files)
    import core.config as cfg
    import pretty_midi
    import soundfile as sf
    import numpy as np

    for i in range(30):
        uid = f"20260602{i:04d}"
        midi = pretty_midi.PrettyMIDI(initial_tempo=120)
        inst = pretty_midi.Instrument(program=0)
        inst.notes.append(pretty_midi.Note(80, 60, 0, 0.5))
        midi.instruments.append(inst)
        midi.write(str(cfg.OUTPUT_DIR / f"{uid}.mid"))
        sf.write(str(cfg.OUTPUT_DIR / f"{uid}.wav"),
                 np.zeros(44100, np.float32), 44100)

    r1 = client.get("/api/history?limit=10&offset=0")
    d1 = r1.json()
    assert d1["ok"] is True
    assert len(d1["entries"]) == 10
    assert d1["total"] >= 30

    r2 = client.get("/api/history?limit=10&offset=10")
    d2 = r2.json()
    assert len(d2["entries"]) == 10

    # Entries should differ between pages
    ids1 = [e["uid"] for e in d1["entries"]]
    ids2 = [e["uid"] for e in d2["entries"]]
    assert ids1 != ids2


def test_history_delete(client, seed_midi, seed_wav):
    r = client.get("/api/history")
    uid = r.json()["entries"][0]["uid"]
    r2 = client.post("/api/history/delete", data={"uid": uid})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
    # Verify deleted
    import core.config as cfg
    remaining = [f.name for f in cfg.OUTPUT_DIR.iterdir() if f.is_file() and f.name.startswith(uid)]
    assert len(remaining) == 0


def test_history_clear(client, seed_midi, seed_wav):
    r = client.post("/api/history/clear")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Verify cleared
    import core.config as cfg
    assert len(list(cfg.OUTPUT_DIR.iterdir())) == 0


def test_history_delete_nonexistent(client):
    r = client.post("/api/history/delete", data={"uid": "nonexistent"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
