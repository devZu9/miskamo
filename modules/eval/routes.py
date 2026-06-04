"""eval module API endpoints."""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from core.config import ROOT

router = APIRouter()
