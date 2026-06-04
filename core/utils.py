"""Utility functions."""

import subprocess
from pathlib import Path

_CYRILLIC_TRANS = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def _transliterate(text):
    """Convert Cyrillic to Latin, spaces to hyphens, strip special chars."""
    result = []
    for ch in text:
        if 'а' <= ch <= 'я' or 'А' <= ch <= 'Я':
            lower = ch.lower()
            t = _CYRILLIC_TRANS.get(lower, '?')
            if not t:
                continue
            result.append(t)
        elif ch == ' ':
            result.append('-')
        elif ch.isascii() and ch.isalnum() or ch in '._-':
            result.append(ch)
    out = ''.join(result).lower()
    return out if out else 'unnamed'


def _ensure_wav(path):
    """Convert non-WAV audio to WAV via ffmpeg. Returns WAV path."""
    ext = path.suffix.lower()
    if ext in (".wav",):
        return path
    wav_path = path.with_suffix(".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ac", "1", "-ar", "44100",
             "-sample_fmt", "s16", str(wav_path)],
            capture_output=True, check=True)
        path.unlink(missing_ok=True)
        return wav_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return path
