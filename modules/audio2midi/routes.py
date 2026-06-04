"""audio2midi module API endpoints."""
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import core.config as cfg
from core.utils import _ensure_wav
from modules.audio2midi.audio2midi import MiskamoEngine

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = MiskamoEngine()
    return _engine


router = APIRouter()


@router.post("/process")
async def api_process(audio: UploadFile = File(...), reverb: bool = Form(True)):
    from datetime import datetime
    ext = Path(audio.filename).suffix.lower() if audio.filename else ".wav"
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    uid = ts
    in_path = cfg.TMP_DIR / f"{uid}_in{ext}"
    out_wav = cfg.OUTPUT_DIR / f"{uid}.wav"
    out_mid = cfg.OUTPUT_DIR / f"{uid}.mid"
    content = await audio.read()
    with open(in_path, "wb") as f:
        f.write(content)
    wav_path = _ensure_wav(in_path)
    if wav_path != in_path:
        in_path = wav_path
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _get_engine().process, str(in_path), str(out_wav), str(out_mid), reverb)
        return JSONResponse({
            "ok": True,
            "audio": f"/api/core/file/{out_wav.name}",
            "midi": f"/api/core/file/{out_mid.name}",
            "filename": ts,
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
