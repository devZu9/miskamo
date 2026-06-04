"""Unified settings endpoint: framework + module settings."""
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from core.config import settings_cache, save_settings, load_settings, LANG
from core.i18n import T

router = APIRouter()


@router.get("/settings")
async def get_settings():
    return dict(settings_cache)


@router.post("/settings")
async def post_settings(
    lang: str = Form("ru"),
    midi_bank: str = Form("maestro"),
    confirm_delete: bool = Form(True),
    toast_sec: int = Form(6),
    clear_tmp: bool = Form(True),
    default_instrument: str = Form("sax"),
    cursor_size: int = Form(24),
    cursor_enabled: bool = Form(False),
    cursor_shape: str = Form("triangle"),
    cursor_angle: int = Form(0),
    cursor_rotation: bool = Form(False),
    cursor_rotation_reverse: bool = Form(False),
    cursor_rotation_speed: int = Form(5),
    cursor_shadow: bool = Form(False),
    cursor_shadow_length: int = Form(10),
    ableton: bool = Form(False),
):
    save_settings({
        "language": lang,
        "midi_bank": midi_bank,
        "confirm_delete": confirm_delete,
        "toast_sec": toast_sec,
        "clear_tmp": clear_tmp,
        "default_instrument": default_instrument,
        "cursor_size": cursor_size,
        "cursor_enabled": cursor_enabled,
        "cursor_shape": cursor_shape,
        "cursor_angle": cursor_angle,
        "cursor_rotation": cursor_rotation,
        "cursor_rotation_reverse": cursor_rotation_reverse,
        "cursor_rotation_speed": cursor_rotation_speed,
        "cursor_shadow": cursor_shadow,
        "cursor_shadow_length": cursor_shadow_length,
        "ableton": ableton,
    })
    global LANG
    LANG = lang
    load_settings()
    return JSONResponse({"ok": True, "message": T("saved")})
