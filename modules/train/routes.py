"""train module API endpoints (stub)."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/train/status")
async def api_train_status():
    return JSONResponse({"ok": True, "message": "Training module — coming soon"})
