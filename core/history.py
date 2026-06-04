"""History listing helpers."""

import re
import soundfile as sf
from .config import OUTPUT_DIR


def _uid_from_name(name):
    """Extract uid by stripping known suffixes."""
    return re.sub(r'_in\..*$|_out\.(wav|mid)$|\.(wav|mid)$', '', name)


def _parse_ts(raw):
    """Format: 20260531091103 → 31.05.2026 09:11:03, else short UUID."""
    if len(raw) == 14 and raw.isdigit():
        y, mo, d = raw[:4], raw[4:6], raw[6:8]
        h, mi, s = raw[8:10], raw[10:12], raw[12:14]
        return f"{d}.{mo}.{y} {h}:{mi}:{s}"
    return raw[:8]


def _history_list(limit=20, offset=0):
    groups = {}
    for f in OUTPUT_DIR.iterdir():
        if not f.is_file():
            continue
        uid = _uid_from_name(f.name)
        groups.setdefault(uid, {})
        groups[uid][f.name] = True
    all_uids = sorted(groups.keys(), key=lambda uid: max(
        (OUTPUT_DIR / fname).stat().st_mtime for fname in groups[uid]
    ), reverse=True)
    total = len(all_uids)
    page = all_uids[offset:offset + limit]
    entries = []
    for uid in page:
        files = groups[uid]
        audio_key = next((k for k in files if k.endswith(".wav")), None)
        midi_key = next((k for k in files if k.endswith(".mid")), None)
        if audio_key and midi_key:
            dur = 0
            try:
                with sf.SoundFile(str(OUTPUT_DIR / audio_key)) as f:
                    dur = round(f.frames / f.samplerate, 1)
            except Exception:
                pass
            entries.append({
                "uid": uid,
                "ts": _parse_ts(uid),
                "duration": dur,
                "audio": f"/api/file/{audio_key}",
                "midi": f"/api/file/{midi_key}",
            })
    return entries, total
