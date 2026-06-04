"""Shared ratings endpoints."""
import csv
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
import core.config as cfg

router = APIRouter()


@router.get("/ratings")
async def api_ratings():
    ratings_file = cfg.RATINGS_FILE
    if not ratings_file.exists():
        return JSONResponse({"rows": []})
    rows = []
    with open(ratings_file) as f:
        reader = csv.reader(f)
        for r in reader:
            rows.append(r)
    return JSONResponse({"rows": rows})


@router.post("/ratings/submit")
async def api_rate(audio: str = Form(""), rating: int = Form(5), note: str = Form("")):
    ratings_file = cfg.RATINGS_FILE
    with open(ratings_file, "a", newline="") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["audio", "rating", "note", "version"])
        w.writerow([audio, rating, note, "miskamo_v1"])
    return JSONResponse({"ok": True})
