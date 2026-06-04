"""Tests UI module."""
from core.module_base import ModuleMeta
from fastapi import APIRouter
from .routes import router

meta = ModuleMeta(
    id="testing",
    tab_key="tests",
    router=router,
    js_files=["tab-tests.js"],
    order=70,
)
