"""Paths, settings, and configuration."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "_shared"

SETTINGS_FILE = ROOT / "core" / "settings.json"
RATINGS_FILE  = SHARED / "_ratings.csv"
DATASET_DIR   = SHARED / "_dataset"
TRAIN_DIR     = SHARED / "_train_output"
MIDI_BANKS    = SHARED / "_midi_banks"
LIBS_DIR       = ROOT / "libs"
SOUNDFONT     = LIBS_DIR / "FluidR3_GM.sf2"
OUTPUT_DIR    = SHARED / "_output"
TMP_DIR       = SHARED / "_tmp"
PRESETS_FILE  = ROOT / "presets.json"
CORRUPT_PRESETS_DIR = SHARED / "_corrupt_presets"
MIDI_GEN_PRESETS_DIR = SHARED / "_midi_gen_presets"

# Framework dirs — created here; module dirs are created by their __init__.py
OUTPUT_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
_clear_tmp = True
if SETTINGS_FILE.exists():
    try:
        _data = json.loads(SETTINGS_FILE.read_text())
        _clear_tmp = _data.get("clear_tmp", True)
    except Exception:
        pass
if _clear_tmp:
    for f in TMP_DIR.iterdir():
        if f.is_file():
            f.unlink()

_DEFAULT_SETTINGS = {
    "language": "ru",
    "midi_bank": "maestro",
    "confirm_delete": True,
    "toast_sec": 6,
    "clear_tmp": True,
    "default_instrument": "sax",
    "cursor_size": 24,
    "cursor_enabled": False,
    "cursor_shape": "triangle",
    "cursor_angle": 0,
    "cursor_rotation": False,
    "cursor_rotation_reverse": False,
    "cursor_rotation_speed": 5,
    "cursor_shadow": True,
    "cursor_shadow_length": 10,
    "ableton": False,
}

settings_cache = {}
LANG = "ru"


def load_settings():
    global LANG
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in _DEFAULT_SETTINGS.items():
            data.setdefault(k, v)
        settings_cache.clear()
        settings_cache.update(data)
        LANG = data.get("language", "ru")
        return data
    settings_cache.clear()
    settings_cache.update(_DEFAULT_SETTINGS)
    LANG = settings_cache.get("language", "ru")
    return settings_cache


def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    settings_cache.clear()
    settings_cache.update(data)


def get_midi_banks():
    banks = []
    if MIDI_BANKS.exists():
        for d in sorted(MIDI_BANKS.iterdir()):
            if d.is_dir():
                c = len(list(d.rglob("*.mid*")))
                if c > 0:
                    banks.append({"name": d.name, "count": c})
    return banks


load_settings()  # initial load
