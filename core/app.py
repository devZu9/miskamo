"""FastAPI application factory."""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PATH", "")
os.environ["PATH"] = str(ROOT / "libs") + os.pathsep + str(ROOT) + os.pathsep + os.environ["PATH"]
os.environ["MPLBACKEND"] = "Agg"

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.module_loader import scan_modules, clear_cache
from core.settings_hub import router as settings_router
from core.router_midi import router as midi_router
from core.router_ratings import router as ratings_router
from core.router_files import router as files_router
from core.i18n import T
from core.config import load_settings, settings_cache, LANG, get_midi_banks, save_settings


def create_app():
    app = FastAPI(title="Miskamo")

    # Mount each module's static/ at /modules/<module_dir>/static/
    _modules_dir = ROOT / "modules"
    if _modules_dir.exists():
        for _entry in sorted(_modules_dir.iterdir()):
            _sdir = _entry / "static"
            if _entry.is_dir() and _sdir.exists():
                app.mount(f"/modules/{_entry.name}/static", StaticFiles(directory=str(_sdir)))

    app.mount("/static/core", StaticFiles(directory=str(ROOT / "core" / "static")), name="core_static")

    # Core API routers — use /api prefix (backward compat)
    load_settings()
    app.include_router(settings_router, prefix="/api")
    app.include_router(midi_router, prefix="/api/core")
    app.include_router(midi_router, prefix="/api")  # backward compat for /api/banks, /api/midi/...
    app.include_router(ratings_router, prefix="/api")
    app.include_router(files_router, prefix="/api")

    # Module routers — use /api prefix to preserve existing paths
    # (routes define their own full path inside the module)
    clear_cache()
    for mod in scan_modules():
        app.include_router(mod.router, prefix="/api")

    # Templates
    templates = Jinja2Templates(directory=ROOT / "templates")
    templates.env.auto_reload = True
    templates.env.globals["T"] = T
    templates.env.globals["LANG"] = LANG

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        load_settings()
        clear_cache()
        modules = scan_modules()
        banks = get_midi_banks()
        return templates.TemplateResponse(request, "index.html", {
            "modules": modules, "banks": banks, "settings": settings_cache,
        })

    @app.get("/lang/{lang}")
    async def set_lang(lang: str):
        if lang in ("ru", "en"):
            settings_cache["language"] = lang
            save_settings(dict(settings_cache))
            load_settings()
        from fastapi.responses import JSONResponse
        return JSONResponse({"ok": True})

    return app
