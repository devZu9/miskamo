"""FluidSynth wrappers — render MIDI notes to WAV audio."""

import io, os
import numpy as np
import pretty_midi
import fluidsynth
from .config import SOUNDFONT

_synth = None
_sfid = None


def _get_synth():
    global _synth, _sfid
    if _synth is None:
        os.environ.setdefault("FLUIDSYNTH_AUDIO_DRIVER", "file")
        _synth = fluidsynth.Synth(gain=0.8, samplerate=44100)
        _sfid = _synth.sfload(str(SOUNDFONT))
        _synth.program_select(0, _sfid, 0, 0)  # piano default
    return _synth


def _render_midi(midi_path, sample_rate=44100, program=None, transpose=0):
    """Render MIDI file → WAV bytes using FluidSynth + SF2."""
    synth = _get_synth()
    synth.system_reset()

    pm = pretty_midi.PrettyMIDI(str(midi_path))
    inst = pm.instruments[0] if pm.instruments else None
    if not inst or not inst.notes:
        return None

    if program is None:
        program = inst.program
    synth.program_select(0, _sfid, 0, program)
    notes = inst.notes

    total_dur = max(n.end for n in notes) + 1.5
    events = []
    for n in notes:
        vel = min(127, max(1, n.velocity))
        pitch = max(0, min(127, n.pitch + transpose))
        events.append((n.start, 'on', pitch, vel))
        events.append((n.end, 'off', pitch, 0))
    events.sort(key=lambda e: e[0])

    chunks, last_time = [], 0.0
    for t, etype, pitch, vel in events:
        dt = t - last_time
        if dt > 0:
            nframes = int(dt * sample_rate)
            if nframes > 0:
                raw = synth.get_samples(nframes)
                arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.float32) / 32768.0
                chunks.append(arr)
                last_time = t
        if etype == 'on':
            synth.noteon(0, pitch, vel)
        else:
            synth.noteoff(0, pitch)

    tail = int((total_dur - last_time) * sample_rate)
    if tail > 0:
        raw = synth.get_samples(tail)
        arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.float32) / 32768.0
        chunks.append(arr)

    audio = np.concatenate(chunks) if chunks else np.zeros(1000, dtype=np.float32)
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    buf = io.BytesIO()
    import soundfile as sf
    sf.write(buf, audio, sample_rate, format='WAV')
    buf.seek(0)
    return buf


def _notes_to_audio(notes, sample_rate=44100, program=0):
    """Render list of pretty_midi.Note → numpy audio via FluidSynth."""
    synth = _get_synth()
    synth.system_reset()
    synth.program_select(0, _sfid, 0, program)
    if not notes:
        return np.zeros(int(sample_rate * 0.5), dtype=np.float32)
    total_dur = max(n.end for n in notes) + 1.5
    events = []
    for n in notes:
        vel = min(127, max(1, n.velocity))
        events.append((n.start, 'on', n.pitch, vel))
        events.append((n.end, 'off', n.pitch, 0))
    events.sort(key=lambda e: e[0])
    chunks, last_time = [], 0.0
    for t, etype, pitch, vel in events:
        dt = t - last_time
        if dt > 0:
            nf = int(dt * sample_rate)
            if nf > 0:
                raw = synth.get_samples(nf)
                arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.float32) / 32768.0
                chunks.append(arr)
                last_time = t
        if etype == 'on':
            synth.noteon(0, pitch, vel)
        else:
            synth.noteoff(0, pitch)
    tail = int((total_dur - last_time) * sample_rate)
    if tail > 0:
        raw = synth.get_samples(tail)
        arr = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.float32) / 32768.0
        chunks.append(arr)
    return np.concatenate(chunks) if chunks else np.zeros(int(sample_rate * 0.5), dtype=np.float32)
