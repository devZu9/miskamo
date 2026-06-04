"""Dataset Generator module."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router
import core.config as cfg

cfg.MIDI_BANKS.mkdir(exist_ok=True)
cfg.DATASET_DIR.mkdir(exist_ok=True)
cfg.CORRUPT_PRESETS_DIR.mkdir(exist_ok=True)

meta = ModuleMeta(
    id="dataset",
    tab_key="dataset",
    router=router,
    js_files=["tab-dataset.js"],
    order=50,
)
