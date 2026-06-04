"""dataset module API endpoints."""
import json, asyncio, random, datetime
import numpy as np
import pretty_midi
import soundfile as sf
from pathlib import Path
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, StreamingResponse
import core.config as cfg
from core.fluidsynth import _notes_to_audio
from core.midi import _truncate_notes, _split_into_segments

_gen_cancel_flag = False
router = APIRouter()


@router.post("/dataset/generate")
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
    global _gen_cancel_flag
    bank_dir = cfg.MIDI_BANKS / bank
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

    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    out_dir = cfg.DATASET_DIR / f"{bank}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "bank": bank, "timestamp": ts,
        "pitch_drift": pitch_drift, "drift_prob": drift_prob,
        "timing_jitter": timing_jitter, "jitter_prob": jitter_prob,
        "bad_notes": bad_notes,
        "noise": noise, "noise_prob": noise_prob,
        "max_dur": max_dur, "split_midi": split_midi,
    }
    (out_dir / "_params.json").write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")

    total_files = min(len(files), 300)
    max_segments_per_file = 1 if not split_midi else 8
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

                if split_midi:
                    segments = _split_into_segments(notes, max_dur)
                else:
                    truncated = _truncate_notes(notes, max_dur)
                    segments = [truncated] if truncated else []

                for seg_idx, clean_notes in enumerate(segments):
                    await asyncio.sleep(0)
                    if _gen_cancel_flag:
                        yield "log:Cancelled by user\n"
                        yield f"result:{json.dumps({'ok': False, 'error': 'cancelled'})}\n"
                        return
                    if len(clean_notes) < 3:
                        skipped += 1
                        yield f"log: [{idx+1}/{total_files}] SKIP {fpath.name} seg {seg_idx+1} (< 3 notes)\n"
                        continue

                    clean_audio = _notes_to_audio(clean_notes, program=0)
                    corrupt_notes = []
                    bad_replaced = 0
                    for n in clean_notes:
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
                    yield f"log: [{idx+1}/{total_files}] OK {serial} {fpath.name}{seg_info}{bad_info}\n"

            except Exception as e:
                skipped += 1
                yield f"log: [{idx+1}/{total_files}] ERR {fpath.name}: {e}\n"

        yield "log:" + "─" * 30 + "\n"
        yield f"log:Done. Generated: {count} pairs | Skipped: {skipped}\n"
        yield f"result:{json.dumps({'ok': True, 'count': count, 'skipped': skipped, 'path': str(out_dir)})}\n"

    return StreamingResponse(event_stream(), media_type="text/plain")


@router.post("/dataset/cancel")
async def api_dataset_cancel():
    global _gen_cancel_flag
    _gen_cancel_flag = True
    return JSONResponse({"ok": True})
