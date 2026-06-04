"""
Miskam'o — FastAPI сервер
Личный музыкальный помощник: голос → MIDI, генератор, датасет, обучение
"""

import os, sys, json, csv, asyncio, re, random
from datetime import datetime
from pathlib import Path

# Must be set before any local imports (fluidsynth, matplotlib)
os.environ.setdefault("PATH", "")
os.environ["PATH"] = str(Path(__file__).parent) + os.pathsep + os.environ["PATH"]
os.environ["MPLBACKEND"] = "Agg"

import numpy as np
import soundfile as sf
import pretty_midi

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from miskamo import MiskamoEngine

from functools import partial
from fastapi import FastAPI, UploadFile, File, Form, Query, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ─── Core modules ──────────────────────────────────────────────────

from core.config import ROOT, SETTINGS_FILE, OUTPUT_DIR, TMP_DIR, DATASET_DIR, MIDI_BANKS, SOUNDFONT, PRESETS_FILE, CORRUPT_PRESETS_DIR

# ─── Cancel flag for dataset generation ─────────────────────────────
_gen_cancel_flag = False
from core.config import settings_cache, LANG, load_settings, save_settings, get_midi_banks, _DEFAULT_SETTINGS
from core.i18n import T
from core.fluidsynth import _get_synth, _render_midi, _notes_to_audio
from core.midi import _truncate_notes, _render_pianoroll, _split_into_segments
from core.history import _history_list
from core.utils import _ensure_wav

# ─── Presets ───────────────────────────────────────────────────────

_CYRILLIC_TRANS = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
}

def _transliterate(text):
    """Convert text to ASCII-safe filename: Cyrillic → Latin, spaces→-, strip special chars."""
    result = []
    for ch in text:
        if ch in _CYRILLIC_TRANS:
            result.append(_CYRILLIC_TRANS[ch])
        elif ch.isalnum() or ch in " ._-":
            result.append(ch)
    s = re.sub(r'\s+', '-', ''.join(result).strip())
    s = re.sub(r'-+', '-', s).strip('-').lower()
    return s or "unnamed"

_PRESET_FIELDS = [
    "pitch_drift", "drift_prob", "timing_jitter", "jitter_prob",
    "bad_notes", "noise", "noise_prob", "max_dur",
    "split_midi",
    "cb_pd", "cb_tj", "cb_bn", "cb_nd", "cb_md",
]

_DEFAULT_PRESETS = {
    "Light": {
        "_name": "Light",
        "pitch_drift": 15, "drift_prob": 30,
        "timing_jitter": 30, "jitter_prob": 30,
        "bad_notes": 2, "noise": 20, "noise_prob": 30,
        "max_dur": 15, "split_midi": True,
        "cb_pd": True, "cb_tj": True, "cb_bn": True, "cb_nd": True, "cb_md": True,
    },
    "Medium": {
        "_name": "Medium",
        "pitch_drift": 30, "drift_prob": 50,
        "timing_jitter": 50, "jitter_prob": 50,
        "bad_notes": 4, "noise": 50, "noise_prob": 50,
        "max_dur": 15, "split_midi": True,
        "cb_pd": True, "cb_tj": True, "cb_bn": True, "cb_nd": True, "cb_md": True,
    },
    "Heavy": {
        "_name": "Heavy",
        "pitch_drift": 50, "drift_prob": 70,
        "timing_jitter": 100, "jitter_prob": 70,
        "bad_notes": 8, "noise": 80, "noise_prob": 70,
        "max_dur": 15, "split_midi": True,
        "cb_pd": True, "cb_tj": True, "cb_bn": True, "cb_nd": True, "cb_md": True,
    },
}


def _load_presets():
    """Return {display_name: params} from _corrupt_presets/ files."""
    CORRUPT_PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    # Migrate old presets.json on first run
    if PRESETS_FILE.exists() and not list(CORRUPT_PRESETS_DIR.glob("*.json")):
        try:
            old = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
            for name, params in old.items():
                params["_name"] = params.get("_name", name)
                safe = _transliterate(params["_name"])
                (CORRUPT_PRESETS_DIR / f"{safe}.json").write_text(
                    json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
            PRESETS_FILE.unlink()
        except Exception:
            pass

    data = {}
    for fp in sorted(CORRUPT_PRESETS_DIR.glob("*.json")):
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
            key = d.get("_name", fp.stem)
            data[key] = d
        except Exception:
            pass

    # Create default presets if completely empty
    if not data:
        for name, params in _DEFAULT_PRESETS.items():
            safe = _transliterate(params["_name"])
            (CORRUPT_PRESETS_DIR / f"{safe}.json").write_text(
                json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
            data[params["_name"]] = params

    return data


def _save_presets(data):
    """Full sync — write all items from dict, delete stale files."""
    CORRUPT_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    written_stems = set()
    for display_name, params in data.items():
        params["_name"] = params.get("_name", display_name)
        safe = _transliterate(params["_name"])
        fp = CORRUPT_PRESETS_DIR / f"{safe}.json"
        fp.write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
        written_stems.add(safe)
    for fp in CORRUPT_PRESETS_DIR.glob("*.json"):
        if fp.stem not in written_stems:
            fp.unlink()


def _api_presets_list():
    return sorted(_load_presets().keys())

# ─── Engine ────────────────────────────────────────────────────────

_engine = None
def _get_engine():
    global _engine
    if _engine is None:
        print(f"[Miskam'o] {T('processing')}...", end=" ", flush=True)
        _engine = MiskamoEngine(instrument="sax")
        print(f"[OK] ({T('ready')})")
    return _engine

# ─── App ───────────────────────────────────────────────────────────

app = FastAPI(title="Miskam'o")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))
templates.env.auto_reload = True
templates.env.globals["T"] = T
templates.env.globals["LANG"] = LANG

# ─── Dataset Presets API ─────────────────────────────────────────────

@app.get("/api/presets")
async def api_presets():
    return JSONResponse({"presets": _api_presets_list()})


# ─── Pages ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, lang: str = None):
    global LANG
    load_settings()
    LANG = settings_cache.get("language", "ru")
    if lang and lang in ("ru", "en"):
        LANG = lang
        settings_cache["language"] = lang
        save_settings(settings_cache)
    banks = get_midi_banks()
    templates.env.globals["LANG"] = LANG
    return templates.TemplateResponse(request, "index.html", {
        "banks": banks, "settings": settings_cache,
    })

@app.get("/lang/{lang}")
async def set_lang(lang: str):
    if lang in ("ru", "en"):
        settings_cache["language"] = lang
        save_settings(dict(settings_cache))
        load_settings()
    return JSONResponse({"ok": True})

# ─── API: Tests ───────────────────────────────────────────────────

@app.post("/api/tests/run")
async def api_tests_run(filter: str = Form("")):
    import subprocess, threading, asyncio

    async def event_stream():
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
        if filter:
            cmd.extend(["-k", filter])
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def target():
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=str(ROOT), bufsize=0,
            )
            for line in iter(proc.stdout.readline, b''):
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    print(f"[Tests] {decoded}", flush=True)
                loop.call_soon_threadsafe(queue.put_nowait, ('line', line))
            proc.wait()
            loop.call_soon_threadsafe(queue.put_nowait, ('done', proc.returncode))

        threading.Thread(target=target, daemon=True).start()

        while True:
            typ, val = await queue.get()
            if typ == 'done':
                yield f"result:{json.dumps({'ok': val == 0, 'returncode': val})}\n"
                break
            decoded = val.decode('utf-8', errors='replace').rstrip()
            if decoded:
                yield f"log:{decoded}\n"

    return StreamingResponse(event_stream(), media_type="text/plain")

# ─── API: Process ──────────────────────────────────────────────────

@app.post("/api/process")
async def api_process(audio: UploadFile = File(...), reverb: bool = Form(True)):
    ext = Path(audio.filename).suffix.lower() if audio.filename else ".wav"
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    uid = ts
    in_path = TMP_DIR / f"{uid}_in{ext}"
    out_wav = OUTPUT_DIR / f"{uid}.wav"
    out_mid = OUTPUT_DIR / f"{uid}.mid"

    content = await audio.read()
    with open(in_path, "wb") as f:
        f.write(content)
    wav_path = _ensure_wav(in_path)
    if wav_path != in_path:
        in_path = wav_path

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _get_engine().process, str(in_path), str(out_wav), str(out_mid), reverb)
        return JSONResponse({
            "ok": True,
            "audio": f"/api/file/{out_wav.name}",
            "midi": f"/api/file/{out_mid.name}",
            "filename": ts,
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

# ─── API: File serving ─────────────────────────────────────────────

@app.get("/api/file/{name}")
async def api_file(name: str, dl: str = None):
    fpath = OUTPUT_DIR / name
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    media_type = None
    download_name = None
    if dl:
        download_name = dl
    elif "_out.mid" in name:
        media_type = "audio/midi"
    elif "_out.wav" in name:
        media_type = "audio/wav"
    return FileResponse(str(fpath), media_type=media_type, filename=download_name)

# ─── API: MIDI piano roll image ────────────────────────────────────

@app.get("/api/midi/pianoroll")
async def api_midi_pianoroll(file: str = "", pitch_low: int = Query(None), pitch_high: int = Query(None), total_bars: int = Query(None), note_offset: int = Query(0)):
    if not file:
        return JSONResponse({"error": "missing file param"}, status_code=400)
    fpath = OUTPUT_DIR / file
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, partial(_render_pianoroll, pitch_low=pitch_low, pitch_high=pitch_high, total_bars=total_bars, note_offset=note_offset), fpath)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ─── API: MIDI render ──────────────────────────────────────────────

@app.get("/api/midi/render")
async def api_midi_render(file: str = "", program: int = None, transpose: int = Query(0)):
    if not file:
        return JSONResponse({"error": "missing file param"}, status_code=400)
    fpath = OUTPUT_DIR / file
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        loop = asyncio.get_event_loop()
        wav_buf = await loop.run_in_executor(None, partial(_render_midi, transpose=transpose), fpath, 44100, program)
        if wav_buf is None:
            return JSONResponse({"error": "no notes in MIDI"}, status_code=400)
        return StreamingResponse(wav_buf, media_type="audio/wav")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ─── API: Ratings ──────────────────────────────────────────────────

@app.get("/api/ratings")
async def api_ratings():
    ratings_file = ROOT / "ratings.csv"
    if not ratings_file.exists():
        return JSONResponse({"rows": []})
    rows = []
    with open(ratings_file) as f:
        reader = csv.reader(f)
        for r in reader:
            rows.append(r)
    return JSONResponse({"rows": rows})

@app.post("/api/rate")
async def api_rate(audio: str = Form(""), rating: int = Form(5), note: str = Form("")):
    ratings_file = ROOT / "ratings.csv"
    with open(ratings_file, "a", newline="") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["audio", "rating", "note", "version"])
        w.writerow([audio, rating, note, "miskamo_v1"])
    return JSONResponse({"ok": True})

# ─── API: MIDI Generator ────────────────────────────────────────────

from core.midi_gen import generate as mg_generate, ALGORITHMS, INSTRUMENTS, SCALES, PROGRESSIONS, DEFAULT_PARAMS

_MIDI_GEN_PRESETS_DIR = CORRUPT_PRESETS_DIR.parent / "_midi_gen_presets"
_MIDI_GEN_PRESETS_DIR.mkdir(exist_ok=True)

def _mg_list():
    presets = {}
    for f in sorted(_MIDI_GEN_PRESETS_DIR.glob("*.json")):
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
        (_MIDI_GEN_PRESETS_DIR / fname).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    # Cleanup removed presets
    existing = set(presets.keys())
    for f in _MIDI_GEN_PRESETS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("_name", f.stem) not in existing:
                f.unlink()
        except Exception:
            pass

@app.get("/api/midi_gen/info")
async def api_midi_gen_info():
    return JSONResponse({
        "algorithms": {k: {"label": v["label"], "desc": v["desc"]} for k, v in ALGORITHMS.items()},
        "instruments": INSTRUMENTS,
        "scales": list(SCALES.keys()),
        "progressions": list(PROGRESSIONS.keys()),
        "defaults": DEFAULT_PARAMS,
    })

@app.post("/api/midi_gen/generate")
async def api_midi_gen_generate(params: str = Form(...)):
    import json, io
    try:
        p = json.loads(params)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Invalid JSON: {e}"})
    from core.midi_gen import validate_params
    p = validate_params(p)
    # If seed is -1, remove it so a random one is generated
    if p.get('_seed') == -1:
        del p['_seed']
    # Pick random key/scale from lists if multiple selected
    if isinstance(p.get("key"), list):
        p["key"] = random.choice(p["key"])
    if isinstance(p.get("scale"), list):
        p["scale"] = random.choice(p["scale"])
    pm = mg_generate(p)
    if pm is None:
        return JSONResponse({"ok": False, "error": "Generation failed (no notes)"})
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    fname = f"gen_{ts}.mid"
    fpath = OUTPUT_DIR / fname
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
        "note_offset": note_offset_param})

@app.post("/api/midi_gen/save_to_bank")
async def api_midi_gen_save_to_bank(params: str = Form(...), bank_name: str = Form("generated")):
    import json, io
    try:
        p = json.loads(params)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Invalid JSON: {e}"})
    from core.midi_gen import validate_params
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
    bank_dir = MIDI_BANKS / _transliterate(bank_name)
    bank_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    fpath = bank_dir / f"gen_{ts}.mid"
    pm.write(str(fpath))
    return JSONResponse({"ok": True, "path": str(fpath), "bank": bank_name})

@app.get("/api/midi_gen/presets")
async def api_midi_gen_presets_list():
    presets = _mg_list()
    return JSONResponse({"ok": True, "presets": [{"name": n, "data": d} for n, d in presets.items()]})

@app.post("/api/midi_gen/presets/save")
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

@app.post("/api/midi_gen/presets/delete")
async def api_midi_gen_presets_delete(name: str = Form(...)):
    presets = _mg_list()
    presets.pop(name, None)
    _mg_save(presets)
    return JSONResponse({"ok": True})

@app.post("/api/midi_gen/presets/rename")
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

@app.get("/api/midi_gen/presets/load")
async def api_midi_gen_presets_load(name: str = ""):
    presets = _mg_list()
    if name not in presets:
        return JSONResponse({"ok": False, "error": "not found"})
    return JSONResponse({"ok": True, "data": presets[name]})

@app.post("/api/midi_gen/generate_batch")
async def api_midi_gen_generate_batch(params: str = Form(...), count: int = Form(8)):
    import json
    try:
        p = json.loads(params)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Invalid JSON: {e}"})
    from core.midi_gen import validate_params
    algo = p.get("algorithm", "scale_walk")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    folder_name = f"{algo}_{ts}"
    safe = _transliterate(folder_name)
    out_dir = MIDI_BANKS / safe
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

# ─── API: Dataset ──────────────────────────────────────────────────

@app.post("/api/dataset/generate")
async def api_dataset_generate(
    bank: str = Form("maestro"),
    pitch_drift: float = Form(30),
    drift_prob: float = Form(50),
    timing_jitter: float = Form(50),
    jitter_prob: float = Form(50),
    bad_notes: float = Form(4),
    noise: float = Form(50),
    noise_prob: float = Form(50),
    max_dur: float = Form(15),
    split_midi: bool = Form(False),
):
    bank_dir = MIDI_BANKS / bank
    if not bank_dir.exists():
        async def err_stream():
            err = json.dumps({"ok": False, "error": f"Bank '{bank}' not found"})
            yield f"result:{err}\n"
        return StreamingResponse(err_stream(), media_type="text/plain")

    files = sorted(bank_dir.rglob("*.mid*"))
    if not files:
        async def err_stream():
            yield f"result:{json.dumps({'ok': False, 'error': 'No MIDI found'})}\n"
        return StreamingResponse(err_stream(), media_type="text/plain")

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    out_dir = DATASET_DIR / f"{bank}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "bank": bank, "timestamp": ts,
        "pitch_drift": pitch_drift, "drift_prob": drift_prob,
        "timing_jitter": timing_jitter, "jitter_prob": jitter_prob,
        "bad_notes": bad_notes,
        "noise": noise, "noise_prob": noise_prob,
        "max_dur": max_dur,
        "split_midi": split_midi,
    }
    (out_dir / "_params.json").write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")

    total_files = min(len(files), 300)
    max_segments_per_file = 1 if not split_midi else 8  # safe upper bound
    pad = len(str(total_files * max_segments_per_file))

    async def event_stream():
        global _gen_cancel_flag
        _gen_cancel_flag = False
        count = 0
        skipped = 0
        rng = np.random.default_rng()
        yield f"log:Bank: {bank} | Output: {out_dir.name}\n"
        yield f"log:Total MIDI files (max 300): {total_files} | Split: {'ON' if split_midi else 'OFF'}\n"
        yield f"log:Max duration: {max_dur}s | Padding: {pad} digits\n"
        yield "log:" + "─" * 30 + "\n"

        for idx, fpath in enumerate(files[:300]):
            await asyncio.sleep(0)
            if _gen_cancel_flag:
                print("[Dataset] Cancelled by user")
                yield "log:Cancelled by user\n"
                yield f"result:{json.dumps({'ok': False, 'error': 'cancelled'})}\n"
                return
            try:
                midi_data = pretty_midi.PrettyMIDI(str(fpath))
                if not midi_data.instruments:
                    skipped += 1
                    yield f"log: [{idx+1}/{total_files}] SKIP {fpath.name} (no instruments)\n"
                    continue
                inst = midi_data.instruments[0]
                if inst.is_drum and len(midi_data.instruments) > 1:
                    inst = midi_data.instruments[1]
                notes = inst.notes
                if len(notes) < 4:
                    skipped += 1
                    yield f"log: [{idx+1}/{total_files}] SKIP {fpath.name} (< 4 notes)\n"
                    continue

                # Determine segments
                if split_midi:
                    segments = _split_into_segments(notes, max_dur)
                else:
                    truncated = _truncate_notes(notes, max_dur)
                    segments = [truncated] if truncated else []

                for seg_idx, clean_notes in enumerate(segments):
                    await asyncio.sleep(0)
                    if _gen_cancel_flag:
                        print("[Dataset] Cancelled by user")
                        yield "log:Cancelled by user\n"
                        yield f"result:{json.dumps({'ok': False, 'error': 'cancelled'})}\n"
                        return
                    if len(clean_notes) < 3:
                        skipped += 1
                        yield f"log: [{idx+1}/{total_files}] SKIP {fpath.name} seg {seg_idx+1} (< 3 notes)\n"
                        continue

                    # ---- Clean WAV ----
                    clean_audio = _notes_to_audio(clean_notes, program=0)

                    # ---- Corrupt WAV (per-note distortions, probabilistic) ----
                    corrupt_notes = []
                    bad_replaced = 0
                    for i, n in enumerate(clean_notes):
                        if rng.random() < drift_prob / 100.0:
                            drift_semi = rng.normal(0, pitch_drift / 100.0)
                            pitch = max(0, min(127, n.pitch + int(round(drift_semi))))
                        else:
                            pitch = n.pitch

                        if rng.random() < jitter_prob / 100.0:
                            jit = rng.normal(0, timing_jitter / 1000.0)
                            start = max(0.0, n.start + jit)
                            end = n.end + jit
                        else:
                            start = n.start
                            end = n.end

                        if end - start < 0.04:
                            continue

                        if rng.random() < bad_notes / 100.0:
                            bad_replaced += 1
                            continue

                        corrupt_notes.append(pretty_midi.Note(
                            velocity=n.velocity, pitch=pitch, start=start, end=end
                        ))

                    if len(corrupt_notes) < 2:
                        skipped += 1
                        yield f"log: [{idx+1}/{total_files}] SKIP {fpath.name} (too few corrupt notes)\n"
                        continue

                    corrupt_audio = _notes_to_audio(corrupt_notes, program=0)

                    # Duration-based noise (across entire audio, not just notes)
                    if noise > 0 and noise_prob > 0:
                        sr = 44100
                        total_len = len(corrupt_audio)
                        target_samples = int(total_len * noise_prob / 100.0)
                        noise_std = (noise / 100.0) * 0.00254
                        if target_samples > 0 and total_len > 0:
                            min_chunk = int(0.03 * sr)
                            max_chunk = int(0.2 * sr)
                            added = 0
                            while added < target_samples:
                                chunk_len = rng.integers(min_chunk, max_chunk + 1)
                                if added + chunk_len > target_samples:
                                    chunk_len = target_samples - added
                                pos = rng.integers(0, total_len - chunk_len)
                                burst = rng.normal(0, noise_std, chunk_len).astype(np.float32)
                                fade = np.minimum(np.arange(chunk_len, dtype=np.float32) / (sr * 0.01), 1.0)
                                fade = np.minimum(fade, fade[::-1])
                                corrupt_audio[pos:pos + chunk_len] += burst * fade
                                added += chunk_len

                    for arr in (clean_audio, corrupt_audio):
                        peak = np.max(np.abs(arr))
                        if peak > 0:
                            arr /= peak * 0.9

                    serial = str(count + 1).zfill(pad)
                    sf.write(str(out_dir / f"{serial}_clean.wav"), clean_audio, 44100)
                    sf.write(str(out_dir / f"{serial}_corrupt.wav"), corrupt_audio, 44100)
                    count += 1
                    bad_info = f" (bad notes: {bad_replaced})" if bad_replaced > 0 else ""
                    seg_info = f" seg {seg_idx+1}/{len(segments)}" if split_midi and len(segments) > 1 else ""
                    print(f"[Dataset] OK ({count}/{total_files}): {fpath.name}{seg_info}{bad_info}")
                    yield f"log: [{idx+1}/{total_files}] OK {serial} {fpath.name}{seg_info}{bad_info}\n"

            except Exception as e:
                skipped += 1
                print(f"[Dataset] ERR: {fpath.name}: {e}")
                yield f"log: [{idx+1}/{total_files}] ERR {fpath.name}: {e}\n"

        yield "log:" + "─" * 30 + "\n"
        yield f"log:Done. Generated: {count} pairs | Skipped: {skipped}\n"
        yield f"result:{json.dumps({'ok': True, 'count': count, 'skipped': skipped, 'path': str(out_dir)})}\n"

    return StreamingResponse(event_stream(), media_type="text/plain")

@app.post("/api/dataset/cancel")
async def api_dataset_cancel():
    global _gen_cancel_flag
    _gen_cancel_flag = True
    return JSONResponse({"ok": True})

# ─── API: History ──────────────────────────────────────────────────

@app.get("/api/history")
async def api_history(limit: int = 20, offset: int = 0):
    entries, total = _history_list(limit, offset)
    return JSONResponse({"ok": True, "entries": entries, "total": total})

@app.post("/api/history/delete")
async def api_history_delete(uid: str = Form(...)):
    for f in OUTPUT_DIR.iterdir():
        if f.name.startswith(uid):
            f.unlink()
    return JSONResponse({"ok": True, "message": T("toast_deleted")})

@app.post("/api/history/clear")
async def api_history_clear():
    for f in OUTPUT_DIR.iterdir():
        f.unlink()
    return JSONResponse({"ok": True})

# ─── API: Settings ─────────────────────────────────────────────────

@app.post("/api/settings")
async def api_settings(
    lang: str = Form("ru"),
    midi_bank: str = Form("maestro"),
    confirm_delete: bool = Form(True),
    toast_sec: int = Form(6),
    clear_tmp: bool = Form(True),
    default_instrument: str = Form("sax"),
    cursor_size: int = Form(24),
    cursor_enabled: bool = Form(False),
    cursor_shape: str = Form("triangle"),
    cursor_angle: int = Form(0),
    cursor_rotation: bool = Form(False),
    cursor_rotation_reverse: bool = Form(False),
    cursor_rotation_speed: int = Form(5),
    cursor_shadow: bool = Form(False),
    cursor_shadow_length: int = Form(10),
    ableton: bool = Form(False),
):
    save_settings({
        "language": lang,
        "midi_bank": midi_bank,
        "confirm_delete": confirm_delete,
        "toast_sec": toast_sec,
        "clear_tmp": clear_tmp,
        "default_instrument": default_instrument,
        "cursor_size": cursor_size,
        "cursor_enabled": cursor_enabled,
        "cursor_shape": cursor_shape,
        "cursor_angle": cursor_angle,
        "cursor_rotation": cursor_rotation,
        "cursor_rotation_reverse": cursor_rotation_reverse,
        "cursor_rotation_speed": cursor_rotation_speed,
        "cursor_shadow": cursor_shadow,
        "cursor_shadow_length": cursor_shadow_length,
        "ableton": ableton,
    })
    global LANG, settings_cache
    LANG = lang
    load_settings()
    return JSONResponse({"ok": True, "message": T("saved")})

# ─── API: Save bank ────────────────────────────────────────────────

@app.get("/api/banks")
async def api_banks():
    return JSONResponse({"ok": True, "banks": get_midi_banks()})

@app.post("/api/banks/rename")
async def api_bank_rename(old_name: str = Form(...), new_name: str = Form(...)):
    safe = _transliterate(new_name)
    old_path = MIDI_BANKS / old_name
    new_path = MIDI_BANKS / safe
    if not old_path.exists():
        return JSONResponse({"ok": False, "error": "not found"})
    if new_path.exists():
        return JSONResponse({"ok": False, "error": "exists"})
    old_path.rename(new_path)
    if settings_cache.get("midi_bank") == old_name:
        settings_cache["midi_bank"] = safe
        save_settings(settings_cache)
    return JSONResponse({"ok": True, "name": safe})

@app.post("/api/banks/delete")
async def api_bank_delete(name: str = Form(...)):
    path = MIDI_BANKS / name
    if not path.exists():
        return JSONResponse({"ok": False, "error": "not found"})
    import shutil
    shutil.rmtree(str(path))
    if settings_cache.get("midi_bank") == name:
        # Fall back to first available bank
        banks = get_midi_banks()
        settings_cache["midi_bank"] = banks[0]["name"] if banks else ""
        save_settings(settings_cache)
    return JSONResponse({"ok": True})

@app.post("/api/save_bank")
async def api_save_bank(midi_bank: str = Form("maestro")):
    load_settings()
    settings_cache["midi_bank"] = midi_bank
    save_settings(settings_cache)
    return JSONResponse({"ok": True})

# ─── Launch ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn, webbrowser, threading
    s = load_settings()
    if s.get("language") not in ("ru", "en"):
        LANG = "ru"
    print(f"\n[Miskam'o] Server: http://127.0.0.1:7890")
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:7890")).start()
    uvicorn.run("main:app", host="127.0.0.1", port=7890, log_level="warning", reload=True)
