"""Shared file serving endpoint."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import core.config as cfg

router = APIRouter()


@router.get("/file/{name}")
async def api_file(name: str, dl: str = None):
    fpath = cfg.OUTPUT_DIR / name
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    media_type = None
    download_name = None
    if dl:
        download_name = dl
    elif "_out.mid" in name:
        media_type = "audio/midi"
    elif "_out.wav" in name:
        media_type = "audio/wav"
    return FileResponse(str(fpath), media_type=media_type, filename=download_name)
