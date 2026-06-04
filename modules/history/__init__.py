"""History module."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router

meta = ModuleMeta(
    id="history",
    tab_key="history",
    router=router,
    js_files=["tab-history.js"],
    order=20,
)
