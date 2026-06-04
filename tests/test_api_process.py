"""Test /api/process endpoint (voice → MIDI)."""

import io
import numpy as np


def test_process_requires_audio(client):
    r = client.post("/api/process")
    assert r.status_code == 422


def test_process_with_wav(client):
    sr = 44100
    wav_data = io.BytesIO()
    import soundfile as sf
    sf.write(wav_data, np.zeros(sr, np.float32), sr, format="WAV")
    wav_data.seek(0)
    r = client.post("/api/process", files={
        "audio": ("test.wav", wav_data, "audio/wav"),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "audio" in data
    assert "midi" in data
    assert "filename" in data


def test_process_creates_output_files(client):
    import soundfile as sf
    sr = 44100
    wav_data = io.BytesIO()
    sf.write(wav_data, np.zeros(sr, np.float32), sr, format="WAV")
    wav_data.seek(0)
    r = client.post("/api/process", files={
        "audio": ("test.wav", wav_data, "audio/wav"),
    })
    assert r.status_code == 200
    data = r.json()
    import main as m
    files = list(m.OUTPUT_DIR.iterdir())
    assert len(files) >= 2  # wav + midi


def test_process_with_reverb(client):
    import soundfile as sf
    wav_data = io.BytesIO()
    sf.write(wav_data, np.zeros(44100, np.float32), 44100, format="WAV")
    wav_data.seek(0)
    r = client.post("/api/process?reverb=true", files={
        "audio": ("test.wav", wav_data, "audio/wav"),
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_process_handles_corrupt_audio(client):
    r = client.post("/api/process", files={
        "audio": ("bad.bin", io.BytesIO(b"\xff\xff\xff\xff"), "application/octet-stream"),
    })
    assert r.status_code == 200
    data = r.json()
    if not data["ok"]:
        assert "error" in data


def test_file_serving(client):
    r = client.get("/api/file/nonexistent.mid")
    assert r.status_code == 404


def test_midi_pianoroll_no_file(client):
    r = client.get("/api/midi/pianoroll")
    assert r.status_code == 400


def test_midi_pianoroll_not_found(client):
    r = client.get("/api/midi/pianoroll?file=nonexistent.mid")
    assert r.status_code == 404


def test_midi_render_no_file(client):
    r = client.get("/api/midi/render")
    assert r.status_code == 400


def test_midi_render_not_found(client):
    r = client.get("/api/midi/render?file=nonexistent.mid")
    assert r.status_code == 404


def test_ratings_empty(client):
    r = client.get("/api/ratings")
    assert r.status_code == 200
    data = r.json()
    assert "rows" in data
    # None or header-only is OK
    assert len(data["rows"]) <= 1


def test_ratings_post(client):
    r = client.post("/api/rate", data={"audio": "test.wav", "rating": 5, "note": "good"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ratings_list(client):
    client.post("/api/rate", data={"audio": "t1.wav", "rating": 4, "note": "ok"})
    client.post("/api/rate", data={"audio": "t2.wav", "rating": 3, "note": "meh"})
    r = client.get("/api/ratings")
    data = r.json()
    assert len(data["rows"]) >= 2
