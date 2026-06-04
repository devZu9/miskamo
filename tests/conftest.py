"""pytest config — module-level mocks + fixtures."""

import io
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# ── Mock miskamo (imports torch, loads GPU model) ──
def _fake_process(in_path, out_wav, out_mid, reverb=True):
    from pathlib import Path
    Path(out_wav).write_bytes(b"RIFF" + b"\x00" * 4092)
    Path(out_mid).write_bytes(b"MThd" + b"\x00" * 10)
    return {
        "audio": Path(out_wav).name,
        "midi": Path(out_mid).name,
        "f0": [260.0, 262.0],
        "notes": [(60, 0.0, 1.0, 80), (62, 1.0, 2.0, 80)],
    }

_mock_engine = MagicMock()
_mock_engine.process.side_effect = _fake_process
_mock_miskamo = MagicMock()
_mock_miskamo.MiskamoEngine = MagicMock(return_value=_mock_engine)
sys.modules["miskamo"] = _mock_miskamo

# ── Mock core.fluidsynth (requires native SF2 + DLLs) ──
_mock_fluidsynth = MagicMock()
_mock_fluidsynth._render_midi = MagicMock(return_value=io.BytesIO(b"RIFF\x00" * 256))
_mock_fluidsynth._notes_to_audio = MagicMock(return_value=np.zeros(44100, np.float32))
_mock_fluidsynth._get_synth = MagicMock(return_value=MagicMock())
sys.modules["core.fluidsynth"] = _mock_fluidsynth

# ── Now import the app (safe — heavy deps are mocked) ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from main import app  # noqa: E402

import pytest  # noqa: E402
import tempfile
import json
import shutil

import main as m  # noqa: E402
import core.config as cfg  # noqa: E402
import core.history as hist  # noqa: E402
import core.midi as midi_mod  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def patch_paths(monkeypatch):
    """Redirect all output/tmp paths to a temp dir for test isolation."""
    tmp = Path(tempfile.mkdtemp(prefix="miskamo_test_"))

    dirs = {
        "OUTPUT_DIR": "_output",
        "TMP_DIR": "_tmp",
        "MIDI_BANKS": "_midi_banks",
        "CORRUPT_PRESETS_DIR": "_corrupt_presets",
        "MIDI_GEN_PRESETS_DIR": "_midi_gen_presets",
        "DATASET_DIR": "dataset",
    }

    paths = {}
    for name, sub in dirs.items():
        p = tmp / sub
        p.mkdir(parents=True, exist_ok=True)
        paths[name] = p

    tmp_settings = tmp / "settings.json"
    tmp_settings.write_text(json.dumps({
        "language": "ru", "midi_bank": "",
 "confirm_delete": True,
        "toast_sec": 3, "clear_tmp": True, "default_instrument": "sax",
        "cursor_size": 24, "cursor_enabled": False, "cursor_shape": "triangle",
        "cursor_angle": 0, "cursor_rotation": False, "cursor_rotation_reverse": False, "cursor_rotation_speed": 5,
        "cursor_shadow": True, "cursor_shadow_length": 10,
    }), encoding="utf-8")

    # Patch core.config paths
    monkeypatch.setattr(cfg, "ROOT", tmp)
    for name, p in paths.items():
        monkeypatch.setattr(cfg, name, p)
    monkeypatch.setattr(cfg, "SETTINGS_FILE", tmp_settings)

    # Patch main module refs (imported as local names)
    monkeypatch.setattr(m, "ROOT", tmp)
    monkeypatch.setattr(m, "OUTPUT_DIR", paths["OUTPUT_DIR"])
    monkeypatch.setattr(m, "TMP_DIR", paths["TMP_DIR"])
    monkeypatch.setattr(m, "MIDI_BANKS", paths["MIDI_BANKS"])
    monkeypatch.setattr(m, "CORRUPT_PRESETS_DIR", paths["CORRUPT_PRESETS_DIR"])
    monkeypatch.setattr(m, "_MIDI_GEN_PRESETS_DIR", paths["MIDI_GEN_PRESETS_DIR"])

    # Patch history module ref
    monkeypatch.setattr(hist, "OUTPUT_DIR", paths["OUTPUT_DIR"])

    # Update settings cache
    cfg.settings_cache.clear()
    cfg.settings_cache.update(json.loads(tmp_settings.read_text(encoding="utf-8")))
    cfg.LANG = "ru"

    yield tmp

    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def seed_midi():
    """Create a minimal test MIDI in OUTPUT_DIR, return path."""
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(initial_tempo=120)
    inst = pretty_midi.Instrument(program=0)
    for i in range(8):
        inst.notes.append(pretty_midi.Note(80, 60 + i, i * 0.5, i * 0.5 + 0.4))
    pm.instruments.append(inst)
    fpath = m.OUTPUT_DIR / "test_0001.mid"
    pm.write(str(fpath))
    return fpath


@pytest.fixture
def seed_wav():
    """Create a minimal test WAV in OUTPUT_DIR, return filename."""
    import soundfile as sf
    fpath = m.OUTPUT_DIR / "test_0001.wav"
    sr = 44100
    sf.write(str(fpath), np.zeros(sr, np.float32), sr)
    return fpath


@pytest.fixture
def seed_bank():
    """Create a minimal MIDI bank dir with one test MIDI."""
    import pretty_midi
    bank = m.MIDI_BANKS / "testbank"
    bank.mkdir(exist_ok=True)
    pm = pretty_midi.PrettyMIDI(initial_tempo=120)
    inst = pretty_midi.Instrument(program=0)
    for i in range(8):
        inst.notes.append(pretty_midi.Note(80, 60 + i, i * 0.5, i * 0.5 + 0.4))
    pm.instruments.append(inst)
    pm.write(str(bank / "0001.mid"))
    return bank
