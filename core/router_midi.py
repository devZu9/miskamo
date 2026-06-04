"""Shared MIDI endpoints: pianoroll, render, banks."""
import asyncio, json, shutil
from functools import partial
from pathlib import Path
from fastapi import APIRouter, Query, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import core.config as cfg
from core.midi import _render_pianoroll
from core.fluidsynth import _render_midi
from core.utils import _transliterate

router = APIRouter()


@router.get("/midi/pianoroll")
async def api_midi_pianoroll(file: str = "", pitch_low: int = Query(None), pitch_high: int = Query(None), total_bars: int = Query(None), note_offset: int = Query(0)):
    if not file:
        return JSONResponse({"error": "missing file param"}, status_code=400)
    fpath = cfg.OUTPUT_DIR / file
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, partial(_render_pianoroll, pitch_low=pitch_low, pitch_high=pitch_high, total_bars=total_bars, note_offset=note_offset), fpath)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/midi/render")
async def api_midi_render(file: str = "", program: int = None, transpose: int = Query(0)):
    if not file:
        return JSONResponse({"error": "missing file param"}, status_code=400)
    fpath = cfg.OUTPUT_DIR / file
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        loop = asyncio.get_event_loop()
        wav_buf = await loop.run_in_executor(None, partial(_render_midi, transpose=transpose), fpath, 44100, program)
        if wav_buf is None:
            return JSONResponse({"error": "no notes in MIDI"}, status_code=400)
        return StreamingResponse(wav_buf, media_type="audio/wav")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/midi/banks")
async def api_banks():
    return JSONResponse({"ok": True, "banks": cfg.get_midi_banks()})


@router.get("/banks")
async def api_banks_legacy():
    return JSONResponse({"ok": True, "banks": cfg.get_midi_banks()})


@router.post("/midi/banks/rename")
async def api_bank_rename(old_name: str = Form(...), new_name: str = Form(...)):
    safe = _transliterate(new_name)
    old_path = cfg.MIDI_BANKS / old_name
    new_path = cfg.MIDI_BANKS / safe
    if not old_path.exists():
        return JSONResponse({"ok": False, "error": "not found"})
    if new_path.exists():
        return JSONResponse({"ok": False, "error": "exists"})
    old_path.rename(new_path)
    if cfg.settings_cache.get("midi_bank") == old_name:
        cfg.settings_cache["midi_bank"] = safe
        cfg.save_settings(cfg.settings_cache)
    return JSONResponse({"ok": True, "name": safe})


@router.post("/banks/rename")
async def api_bank_rename_legacy(old_name: str = Form(...), new_name: str = Form(...)):
    safe = _transliterate(new_name)
    old_path = cfg.MIDI_BANKS / old_name
    new_path = cfg.MIDI_BANKS / safe
    if not old_path.exists():
        return JSONResponse({"ok": False, "error": "not found"})
    if new_path.exists():
        return JSONResponse({"ok": False, "error": "exists"})
    old_path.rename(new_path)
    if cfg.settings_cache.get("midi_bank") == old_name:
        cfg.settings_cache["midi_bank"] = safe
        cfg.save_settings(cfg.settings_cache)
    return JSONResponse({"ok": True, "name": safe})


@router.post("/midi/banks/delete")
async def api_bank_delete(name: str = Form(...)):
    path = cfg.MIDI_BANKS / name
    if not path.exists():
        return JSONResponse({"ok": False, "error": "not found"})
    shutil.rmtree(str(path))
    if cfg.settings_cache.get("midi_bank") == name:
        banks = cfg.get_midi_banks()
        cfg.settings_cache["midi_bank"] = banks[0]["name"] if banks else ""
        cfg.save_settings(cfg.settings_cache)
    return JSONResponse({"ok": True})


@router.post("/banks/delete")
async def api_bank_delete_legacy(name: str = Form(...)):
    path = cfg.MIDI_BANKS / name
    if not path.exists():
        return JSONResponse({"ok": False, "error": "not found"})
    shutil.rmtree(str(path))
    if cfg.settings_cache.get("midi_bank") == name:
        banks = cfg.get_midi_banks()
        cfg.settings_cache["midi_bank"] = banks[0]["name"] if banks else ""
        cfg.save_settings(cfg.settings_cache)
    return JSONResponse({"ok": True})


@router.post("/midi/banks/save")
async def api_save_bank(midi_bank: str = Form("maestro")):
    cfg.load_settings()
    cfg.settings_cache["midi_bank"] = midi_bank
    cfg.save_settings(cfg.settings_cache)
    return JSONResponse({"ok": True})


@router.post("/save_bank")
async def api_save_bank_legacy(midi_bank: str = Form("maestro")):
    cfg.load_settings()
    cfg.settings_cache["midi_bank"] = midi_bank
    cfg.save_settings(cfg.settings_cache)
    return JSONResponse({"ok": True})
