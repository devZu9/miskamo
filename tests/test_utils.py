"""Test utility functions: _transliterate, _uid_from_name, _parse_ts, _ensure_wav."""

from core.history import _uid_from_name, _parse_ts
from main import _transliterate


def test_transliterate_cyrillic():
    assert _transliterate("Привет") == "privet"
    assert _transliterate("Тестовый пресет") == "testovyy-preset"
    assert _transliterate("Щука") == "shchuka"


def test_transliterate_spaces():
    assert _transliterate("hello world") == "hello-world"


def test_transliterate_special_chars():
    assert _transliterate("test@#$preset!") == "testpreset"


def test_transliterate_mixed():
    assert _transliterate("Привет World 42") == "privet-world-42"


def test_transliterate_empty():
    assert _transliterate("") == "unnamed"


def test_transliterate_only_special():
    assert _transliterate("@@@###") == "unnamed"


def test_transliterate_dots_and_hyphens():
    result = _transliterate("My.Preset-Test v2")
    assert "-" in result
    assert "." in result


def test_uid_from_name_in_wav():
    assert _uid_from_name("20260531091103_out.wav") == "20260531091103"


def test_uid_from_name_in_mid():
    assert _uid_from_name("20260531091103_out.mid") == "20260531091103"


def test_uid_from_name_in_file():
    assert _uid_from_name("20260531091103_in.wav") == "20260531091103"


def test_uid_from_name_no_suffix():
    assert _uid_from_name("20260531091103") == "20260531091103"


def test_uid_from_name_with_extra():
    result = _uid_from_name("12345_some_extra.mid")
    assert result in ("12345", "12345_some_extra")


def test_parse_ts_valid():
    result = _parse_ts("20260531091103")
    assert "31.05.2026" in result
    assert "09:11:03" in result


def test_parse_ts_short():
    result = _parse_ts("abc12345")
    assert result == "abc12345"


def test_parse_ts_non_digit():
    result = _parse_ts("abcdefghijklmn")
    assert result == "abcdefgh"


def test_parse_ts_empty():
    result = _parse_ts("")
    assert result == ""


def test_ensure_wav_passthrough(tmp_path):
    from core.utils import _ensure_wav
    wav = tmp_path / "test.wav"
    wav.write_text("dummy")
    result = _ensure_wav(wav)
    assert result == wav


def test_ensure_wav_non_wav_without_ffmpeg(tmp_path):
    from core.utils import _ensure_wav
    non_wav = tmp_path / "test.mp3"
    non_wav.write_text("dummy")
    # Without ffmpeg, should return original path
    result = _ensure_wav(non_wav)
    # Either returns original (ffmpeg not found) or returns wav
    assert result.suffix in (".mp3", ".wav")
