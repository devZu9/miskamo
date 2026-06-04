"""Scans modules/ directory and loads ModuleMeta."""
import sys
from pathlib import Path
from core.module_base import ModuleMeta

MODULES_DIR = Path(__file__).resolve().parent.parent / "modules"
_cache = None


def scan_modules():
    global _cache
    if _cache is not None:
        return _cache

    _cache = []
    if not MODULES_DIR.exists():
        return _cache

    for entry in sorted(MODULES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        init_file = entry / "__init__.py"
        if not init_file.exists():
            continue
        mod_name = entry.name
        # Add parent dir to path so relative imports work
        if str(MODULES_DIR.parent) not in sys.path:
            sys.path.insert(0, str(MODULES_DIR.parent))
        try:
            mod = __import__(f"modules.{mod_name}", fromlist=["meta"])
            if hasattr(mod, 'meta'):
                _cache.append(mod.meta)
        except Exception:
            import traceback
            traceback.print_exc()

    _cache.sort(key=lambda m: m.order)
    return _cache


def clear_cache():
    global _cache
    _cache = None
