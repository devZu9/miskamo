import json
from pathlib import Path
from . import config

_lang_dir = Path(__file__).resolve().parent.parent / "lang"
_L10N = {}
_last_mtime = {}

def _ensure_loaded():
    for fp in sorted(_lang_dir.glob("*.json")):
        code = fp.stem
        mtime = fp.stat().st_mtime
        if code not in _last_mtime or _last_mtime[code] != mtime:
            with open(fp, encoding="utf-8") as fh:
                _L10N[code] = json.load(fh)
            _last_mtime[code] = mtime

def T(key):
    _ensure_loaded()
    return _L10N.get(config.LANG, _L10N.get("ru", {})).get(key, key)
