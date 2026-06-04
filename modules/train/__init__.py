"""Train module (stub)."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router
import core.config as cfg

cfg.TRAIN_DIR.mkdir(exist_ok=True)

meta = ModuleMeta(
    id="train",
    tab_key="train",
    router=router,
    js_files=["tab-train.js"],
    order=60,
)
