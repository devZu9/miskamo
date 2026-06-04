"""Test core.config: settings load/save, defaults, banks."""

import json
import pytest


def test_default_settings():
    from core.config import _DEFAULT_SETTINGS, settings_cache
    defaults = _DEFAULT_SETTINGS
    assert defaults["language"] == "ru"
    assert defaults["midi_bank"] == "maestro"
    assert defaults["default_instrument"] == "sax"
    assert defaults["toast_sec"] == 6
    assert settings_cache["language"] == "ru"


def test_save_and_load_roundtrip():
    from core.config import save_settings, load_settings, SETTINGS_FILE
    data = {
        "language": "en",
        "midi_bank": "testbank",
        "confirm_delete": False,
        "toast_sec": 10,
        "clear_tmp": False,
        "default_instrument": "flute",
    }
    save_settings(data)
    loaded = load_settings()
    for k, v in data.items():
        assert loaded[k] == v, f"Mismatch for {k}: {loaded.get(k)} != {v}"


def test_settings_persistence():
    from core.config import save_settings, load_settings
    data = {"language": "en", "midi_bank": "x",
            "confirm_delete": False, "toast_sec": 9, "clear_tmp": False,
            "default_instrument": "piano", "cursor_size": 24, "cursor_enabled": False, "cursor_shape": "circle",
            "cursor_angle": 0, "cursor_rotation": False, "cursor_rotation_reverse": False, "cursor_rotation_speed": 5,
            "cursor_shadow": True, "cursor_shadow_length": 10, "ableton": False}
    save_settings(data)
    loaded = load_settings()
    assert loaded == data


def test_settings_cache_mutates_in_place():
    from core.config import settings_cache, save_settings, load_settings
    save_settings({"language": "en", "midi_bank": "x",
                   "confirm_delete": True, "toast_sec": 6, "clear_tmp": True,
                    "default_instrument": "sax", "cursor_size": 24, "cursor_enabled": False, "cursor_shape": "circle",
                    "cursor_angle": 0, "cursor_rotation": False, "cursor_rotation_reverse": False, "cursor_rotation_speed": 5,
                    "cursor_shadow": True, "cursor_shadow_length": 10})
    load_settings()
    ref = id(settings_cache)
    load_settings()
    assert id(settings_cache) == ref, "settings_cache was reassigned, not mutated"


def test_settings_cache_update_in_place():
    from core.config import settings_cache, load_settings
    load_settings()
    old_id = id(settings_cache)
    from core.config import save_settings
    save_settings({"language": "en", "midi_bank": "x",
                   "confirm_delete": True, "toast_sec": 6, "clear_tmp": True,
                    "default_instrument": "sax", "cursor_size": 24, "cursor_enabled": False, "cursor_shape": "circle",
                    "cursor_angle": 0, "cursor_rotation": False, "cursor_rotation_reverse": False, "cursor_rotation_speed": 5,
                    "cursor_shadow": True, "cursor_shadow_length": 10})
    assert id(settings_cache) == old_id


def test_missing_settings_file_loads_defaults(monkeypatch, tmp_path):
    import core.config as cfg
    missing = tmp_path / "nosettings.json"
    monkeypatch.setattr(cfg, "SETTINGS_FILE", missing)
    data = cfg.load_settings()
    for k, v in cfg._DEFAULT_SETTINGS.items():
        assert data[k] == v


def test_partial_settings_file(monkeypatch, tmp_path):
    import core.config as cfg
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"language": "en"}), encoding="utf-8")
    monkeypatch.setattr(cfg, "SETTINGS_FILE", partial)
    data = cfg.load_settings()
    assert data["language"] == "en"
    assert data["default_instrument"] == "sax"


def test_get_midi_banks_empty():
    from core.config import get_midi_banks
    banks = get_midi_banks()
    assert banks == []


def test_get_midi_banks_with_data(seed_bank):
    from core.config import get_midi_banks, MIDI_BANKS
    banks = get_midi_banks()
    names = [b["name"] for b in banks]
    assert "testbank" in names
    tb = next(b for b in banks if b["name"] == "testbank")
    assert tb["count"] >= 1


def test_get_midi_banks_filters_empty_dirs():
    from core.config import get_midi_banks, MIDI_BANKS
    empty = MIDI_BANKS / "empty_dir"
    empty.mkdir()
    banks = get_midi_banks()
    names = [b["name"] for b in banks]
    assert "empty_dir" not in names


def test_lang_global_updated_on_load():
    from core.config import LANG, load_settings
    load_settings()
    assert LANG == "ru"
