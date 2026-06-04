"""MIDI helpers — truncation and piano roll rendering."""

import io
import pretty_midi
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import librosa.display


def _truncate_notes(notes, max_dur):
    """Clip note ends to max_dur; skip notes starting after max_dur."""
    out = []
    for n in notes:
        if n.start >= max_dur:
            continue
        end = min(n.end, max_dur)
        if end - n.start < 0.05:
            continue
        out.append(pretty_midi.Note(velocity=n.velocity, pitch=n.pitch, start=n.start, end=end))
    return out


def _extract_segment(notes, offset, duration):
    """Extract notes within [offset, offset+duration), shift to start at 0."""
    out = []
    end_t = offset + duration
    for n in notes:
        if n.end <= offset or n.start >= end_t:
            continue
        start = max(n.start, offset) - offset
        n_end = min(n.end, end_t) - offset
        if n_end - start < 0.05:
            continue
        out.append(pretty_midi.Note(velocity=n.velocity, pitch=n.pitch, start=start, end=n_end))
    return out


def _split_into_segments(notes, max_dur):
    """Split notes into segments of max_dur each. Merges short tail with last segment."""
    if not notes:
        return []
    total_dur = max(n.end for n in notes)
    if total_dur <= max_dur:
        seg = _truncate_notes(notes, max_dur)
        return [seg] if seg else []

    segments = []
    start = 0.0
    while start < total_dur:
        end = start + max_dur
        remaining = total_dur - end
        if remaining > 0 and remaining < max_dur:
            end = total_dur
        seg = _extract_segment(notes, start, end - start)
        if seg:
            segments.append(seg)
        start = end
        if end >= total_dur:
            break
    return segments


def _render_pianoroll(midi_path, pitch_low=None, pitch_high=None, total_bars=None, note_offset=0):
    """Generate piano roll PNG image from MIDI file (matplotlib + librosa)."""
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    if note_offset:
        for instr in pm.instruments:
            for n in instr.notes:
                n.pitch -= note_offset
    fs = 50
    if pitch_low is None:
        pitch_low = 21
    if pitch_high is None:
        pitch_high = 108
    start_pitch, end_pitch = pitch_low, pitch_high + 1
    roll = pm.get_piano_roll(fs=fs)[start_pitch:end_pitch]

    # Add tiny gaps between consecutive same-pitch notes so they don't merge visually
    if pm.instruments:
        for instr in pm.instruments:
            notes = sorted(instr.notes, key=lambda n: (n.pitch, n.start))
            prev = None
            for n in notes:
                if prev is not None and prev.pitch == n.pitch:
                    gap_start_f = int(prev.end * fs)
                    gap_end_f = int(n.start * fs)
                    if 0 < gap_end_f - gap_start_f < 4:
                        mid_f = (gap_start_f + gap_end_f) // 2
                        row = n.pitch - start_pitch
                        if 0 <= row < roll.shape[0] and mid_f < roll.shape[1]:
                            roll[row, max(0, mid_f - 1):min(roll.shape[1], mid_f + 1)] = 0
                prev = n

    fig, ax = plt.subplots(figsize=(10, 4))
    img = librosa.display.specshow(
        roll, hop_length=1, sr=fs,
        x_axis='time', y_axis='cqt_note',
        fmin=pretty_midi.note_number_to_hz(start_pitch),
        ax=ax, cmap='magma'
    )
    # Show all semitones on y-axis
    __NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    tick_hz = [pretty_midi.note_number_to_hz(p) for p in range(start_pitch, end_pitch + 1)]
    tick_labels = [f"{__NOTE_NAMES[p%12]}{p//12-1}" for p in range(start_pitch, end_pitch + 1)]
    ax.set_yticks(tick_hz)
    ax.set_yticklabels(tick_labels, fontsize=7)
    # X-axis: show bars instead of seconds
    tempos = pm.get_tempo_changes()
    bpm = max(tempos[1][0] if len(tempos[1]) > 0 else 120, 1)
    beats_per_bar = pm.time_signature_changes[0].numerator if pm.time_signature_changes else 4
    bar_sec = beats_per_bar / bpm * 60
    if total_bars is not None:
        bar_ticks = [i * bar_sec for i in range(total_bars)]
    else:
        total_sec = roll.shape[1] / fs
        num_bars = int(total_sec / bar_sec) + 2
        bar_ticks = [i * bar_sec for i in range(num_bars) if i * bar_sec <= total_sec]
    ax.set_xticks(bar_ticks)
    ax.set_xticklabels([str(i + 1) for i in range(len(bar_ticks))], fontsize=8)
    fig.colorbar(img, ax=ax, format='%+2.0f dB')
    ax.set_ylabel('')
    ax.set_xlabel('Bar')
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf
