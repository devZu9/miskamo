"""Test i18n: all translation keys present in both lang files."""

import json
from pathlib import Path

import pytest

LANG_DIR = Path(__file__).resolve().parent.parent / "core" / "lang"


def _load_lang(code):
    fp = LANG_DIR / f"{code}.json"
    assert fp.exists(), f"Missing lang file: {fp}"
    with open(fp, encoding="utf-8") as f:
        return json.load(f)


def test_all_keys_in_both_langs():
    en = _load_lang("en")
    ru = _load_lang("ru")
    en_keys = set(en.keys())
    ru_keys = set(ru.keys())
    missing_in_ru = en_keys - ru_keys
    missing_in_en = ru_keys - en_keys
    assert not missing_in_ru, f"Keys in en.json but missing in ru.json: {missing_in_ru}"
    assert not missing_in_en, f"Keys in ru.json but missing in en.json: {missing_in_en}"


def test_no_empty_values():
    for code in ("en", "ru"):
        data = _load_lang(code)
        empty = [k for k, v in data.items() if not v]
        assert not empty, f"Empty values in {code}.json: {empty}"


def test_no_missing_values():
    en = _load_lang("en")
    ru = _load_lang("ru")
    for key in en:
        assert en[key], f"Empty en value for {key}"
        assert ru.get(key), f"Missing/empty ru value for {key}"


@pytest.mark.parametrize("code", ["ru", "en"])
def test_lang_file_valid_json(code):
    fp = LANG_DIR / f"{code}.json"
    raw = fp.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)
    assert len(data) > 100


def test_T_returns_key_for_missing():
    from core.i18n import T
    import core.config as cfg
    cfg.LANG = "en"
    result = T("_nonexistent_key_12345")
    assert result == "_nonexistent_key_12345"


def test_T_returns_translation():
    from core.i18n import T
    import core.config as cfg
    cfg.LANG = "en"
    title = T("title")
    assert title and isinstance(title, str)
    assert len(title) > 0

    cfg.LANG = "ru"
    title_ru = T("title")
    assert title_ru and isinstance(title_ru, str)
    assert len(title_ru) > 0
