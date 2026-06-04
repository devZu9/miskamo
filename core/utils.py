"""Utility functions."""

import subprocess
from pathlib import Path


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
