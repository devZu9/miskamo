"""history module API endpoints."""
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
import core.config as cfg
from modules.history.history import _history_list

router = APIRouter()


@router.get("/history")
async def api_history(limit: int = 20, offset: int = 0):
    entries, total = _history_list(limit, offset)
    return JSONResponse({"ok": True, "entries": entries, "total": total})


@router.post("/history/delete")
async def api_history_delete(uid: str = Form(...)):
    for f in cfg.OUTPUT_DIR.iterdir():
        if f.name.startswith(uid):
            f.unlink()
    return JSONResponse({"ok": True, "message": "Deleted"})


@router.post("/history/clear")
async def api_history_clear():
    for f in cfg.OUTPUT_DIR.iterdir():
        f.unlink()
    return JSONResponse({"ok": True})
