"""Eval module."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router as eval_router

meta = ModuleMeta(
    id="eval",
    tab_key="eval",
    router=eval_router,
    js_files=[],
    order=15,
)
