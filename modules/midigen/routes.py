"""midigen module API endpoints."""
import json, random, datetime
from pathlib import Path
from fastapi import APIRouter, Form, Query
from fastapi.responses import JSONResponse
import core.config as cfg
from core.utils import _transliterate
from modules.midigen.midi_gen import generate as mg_generate, ALGORITHMS, INSTRUMENTS, SCALES, PROGRESSIONS, DEFAULT_PARAMS

router = APIRouter()


def _mg_presets_dir():
    return cfg.MIDI_GEN_PRESETS_DIR


def _mg_list():
    presets = {}
    for f in sorted(_mg_presets_dir().glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            name = data.get("_name", f.stem)
            presets[name] = data
        except Exception:
            pass
    return presets


def _mg_save(presets):
    for name, data in presets.items():
        fname = _transliterate(name) + ".json"
        (_mg_presets_dir() / fname).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    existing = set(presets.keys())
    for f in _mg_presets_dir().glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("_name", f.stem) not in existing:
                f.unlink()
        except Exception:
            pass


@router.get("/midi_gen/info")
async def api_midi_gen_info():
    return JSONResponse({
        "algorithms": {k: {"label": v["label"], "desc": v["desc"]} for k, v in ALGORITHMS.items()},
        "instruments": INSTRUMENTS,
        "scales": list(SCALES.keys()),
        "progressions": list(PROGRESSIONS.keys()),
        "defaults": DEFAULT_PARAMS,
    })


@router.post("/midi_gen/generate")
async def api_midi_gen_generate(params: str = Form(...)):
    import json as _json
    try:
        p = _json.loads(params)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Invalid JSON: {e}"})
    from modules.midigen.midi_gen import validate_params
    p = validate_params(p)
    if p.get('_seed') == -1:
        del p['_seed']
    if isinstance(p.get("key"), list):
        p["key"] = random.choice(p["key"])
    if isinstance(p.get("scale"), list):
        p["scale"] = random.choice(p["scale"])
    pm = mg_generate(p)
    if pm is None:
        return JSONResponse({"ok": False, "error": "Generation failed (no notes)"})
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    fname = f"gen_{ts}.mid"
    fpath = cfg.OUTPUT_DIR / fname
    pm.write(str(fpath))
    pitch_low = p.get('note_range_low')
    pitch_high = p.get('note_range_high')
    total_bars = p.get('total_bars')
    note_offset = p.get('note_offset', 0)
    note_offset_param = 0
    if pitch_low is not None:
        pitch_low += 12
        pitch_high += 12
        note_offset_param = note_offset - 12
    return JSONResponse({"ok": True, "filename": fname, "seed": p.get('_seed'),
        "pitch_low": pitch_low, "pitch_high": pitch_high, "total_bars": total_bars,
        "note_offset": note_offset_param,
        "key": p.get('key'), "scale": p.get('scale')})


@router.post("/midi_gen/save_to_bank")
async def api_midi_gen_save_to_bank(params: str = Form(...), bank_name: str = Form("generated")):
    import json as _json
    try:
        p = _json.loads(params)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Invalid JSON: {e}"})
    from modules.midigen.midi_gen import validate_params
    p = validate_params(p)
    if p.get('_seed') == -1:
        del p['_seed']
    if isinstance(p.get("key"), list):
        p["key"] = random.choice(p["key"])
    if isinstance(p.get("scale"), list):
        p["scale"] = random.choice(p["scale"])
    pm = mg_generate(p)
    if pm is None:
        return JSONResponse({"ok": False, "error": "Generation failed (no notes)"})
    bank_dir = cfg.MIDI_BANKS / _transliterate(bank_name)
    bank_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    fpath = bank_dir / f"gen_{ts}.mid"
    pm.write(str(fpath))
    return JSONResponse({"ok": True, "path": str(fpath), "bank": bank_name})


@router.get("/midi_gen/presets")
async def api_midi_gen_presets_list():
    presets = _mg_list()
    return JSONResponse({"ok": True, "presets": [{"name": n, "data": d} for n, d in presets.items()]})


@router.post("/midi_gen/presets/save")
async def api_midi_gen_presets_save(name: str = Form(...), params: str = Form(...), overwrite: bool = Form(False)):
    presets = _mg_list()
    if name in presets and not overwrite:
        return JSONResponse({"ok": False, "error": "exists"})
    try:
        data = json.loads(params)
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON"})
    data["_name"] = name
    presets[name] = data
    _mg_save(presets)
    return JSONResponse({"ok": True})


@router.post("/midi_gen/presets/delete")
async def api_midi_gen_presets_delete(name: str = Form(...)):
    presets = _mg_list()
    presets.pop(name, None)
    _mg_save(presets)
    return JSONResponse({"ok": True})


@router.post("/midi_gen/presets/rename")
async def api_midi_gen_presets_rename(old_name: str = Form(...), new_name: str = Form(...), overwrite: bool = Form(False)):
    presets = _mg_list()
    if old_name not in presets:
        return JSONResponse({"ok": False, "error": "not found"})
    if new_name in presets and not overwrite:
        return JSONResponse({"ok": False, "error": "exists"})
    presets[new_name] = presets.pop(old_name)
    presets[new_name]["_name"] = new_name
    _mg_save(presets)
    return JSONResponse({"ok": True})


@router.get("/midi_gen/presets/load")
async def api_midi_gen_presets_load(name: str = ""):
    presets = _mg_list()
    if name not in presets:
        return JSONResponse({"ok": False, "error": "not found"})
    return JSONResponse({"ok": True, "data": presets[name]})


@router.post("/midi_gen/generate_batch")
async def api_midi_gen_generate_batch(params: str = Form(...), count: int = Form(8)):
    import json as _json, datetime as _dt
    try:
        p = _json.loads(params)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Invalid JSON: {e}"})
    from modules.midigen.midi_gen import validate_params
    algo = p.get("algorithm", "scale_walk")
    ts = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
    folder_name = f"{algo}_{ts}"
    safe = _transliterate(folder_name)
    out_dir = cfg.MIDI_BANKS / safe
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for i in range(count):
        seed = i + 1 + hash(repr(p)) % 2**31
        pp = dict(p)
        pp["_seed"] = seed
        pp = validate_params(pp)
        if isinstance(pp.get("key"), list):
            pp["key"] = random.choice(pp["key"])
        if isinstance(pp.get("scale"), list):
            pp["scale"] = random.choice(pp["scale"])
        pm = mg_generate(pp)
        if pm is None:
            continue
        fname = f"{i+1:04d}.mid"
        pm.write(str(out_dir / fname))
        generated += 1
    return JSONResponse({"ok": True, "count": generated, "path": str(out_dir)})
