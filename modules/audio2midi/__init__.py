"""Audio-to-MIDI module."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router

meta = ModuleMeta(
    id="audio2midi",
    tab_key="process",
    router=router,
    js_files=["tab-audio2midi.js"],
    order=10,
)
meta.module_dir = "audio2midi"
