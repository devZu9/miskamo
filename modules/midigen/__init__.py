"""MIDI Generator module."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router
import core.config as cfg

cfg.MIDI_BANKS.mkdir(exist_ok=True)

meta = ModuleMeta(
    id="midigen",
    tab_key="midigen",
    router=router,
    js_files=["tab-midigen.js"],
    order=30,
)
