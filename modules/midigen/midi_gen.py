"""Procedural MIDI melody generation — 5 algorithms."""
import math, random, json
from pathlib import Path
import pretty_midi

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

SCALES = {
    'major': [0,2,4,5,7,9,11], 'minor': [0,2,3,5,7,8,10],
    'pentatonic_major': [0,2,4,7,9], 'pentatonic_minor': [0,3,5,7,10],
    'blues': [0,3,5,6,7,10],
    'dorian': [0,2,3,5,7,9,10], 'phrygian': [0,1,3,5,7,8,10],
    'lydian': [0,2,4,6,7,9,11], 'mixolydian': [0,2,4,5,7,9,10],
    'locrian': [0,1,3,5,7,8,10], 'chromatic': list(range(12)),
}

PROGRESSIONS = {
    'pop': ['I','V','vi','IV'], 'edm': ['I','V','vi','IV'],
    'rock': ['I','IV','V'],
    'blues_12': ['I','I','I','I','IV','IV','I','I','V','V','I','I'],
    'jazz': ['ii','V','I'], 'classical': ['I','IV','V','I'],
    'rap': ['i','iv','v'], 'reggae': ['I','IV'],
}

CHORD_TONES = {
    'maj': {'I':[0,4,7], 'II':[2,6,9], 'III':[4,8,11], 'IV':[5,9,0], 'V':[7,11,2], 'VI':[9,1,4], 'VII':[11,3,6]},
    'min': {'i':[0,3,7], 'ii°':[2,5,8], 'III':[3,7,10], 'iv':[5,8,0], 'v':[7,10,2], 'VI':[8,0,3], 'VII':[10,2,5]},
}

MARKOV_MATRICES = {
    'generic': [
        [0.10,0.15,0.20,0.15,0.25,0.10,0.05],
        [0.05,0.10,0.20,0.25,0.25,0.10,0.05],
        [0.10,0.20,0.10,0.15,0.30,0.10,0.05],
        [0.15,0.10,0.15,0.10,0.35,0.10,0.05],
        [0.25,0.10,0.10,0.10,0.10,0.15,0.20],
        [0.20,0.15,0.10,0.15,0.25,0.10,0.05],
        [0.15,0.15,0.20,0.15,0.25,0.05,0.05],
    ],
}

INSTRUMENTS = [
    {'id':0,'name':'piano'},{'id':25,'name':'guitar'},{'id':33,'name':'bass'},
    {'id':41,'name':'violin'},{'id':56,'name':'trumpet'},{'id':65,'name':'sax'},
    {'id':73,'name':'flute'},{'id':14,'name':'vibraphone'},
    {'id':118,'name':'synth_pad'},{'id':128,'name':'drums'},
]


DURATIONS = [0.25,0.5,1,1.5,2,3,4]
DUR_WEIGHTS = [0.05,0.2,0.3,0.15,0.2,0.05,0.05]

def _rng(params):
    return random.Random(params.get('_seed'))

def _scale_notes(root, scale_semitones, lo, hi):
    notes = []
    for oct in range(0, 10):
        for s in scale_semitones:
            n = oct*12 + root + s
            if lo <= n <= hi:
                notes.append(n)
    return sorted(notes)

def _pick_duration(rng_obj, dur_pool, dur_weights_pool, beats_left):
    candidates = [d for d in dur_pool if d <= beats_left + 1e-9]
    if not candidates:
        return beats_left
    w = [dur_weights_pool[dur_pool.index(d)] for d in candidates]
    return rng_obj.choices(candidates, weights=w, k=1)[0]

def _interval_weight(interval, mu=2, sigma=2.5):
    return math.exp(-((interval-mu)**2)/(2*sigma**2))

def gen_scale_walk(root, scale_semitones, params):
    rng_obj = _rng(params)
    bpm = params.get('bpm', 120)
    max_int = params.get('max_interval', 7)
    rest_prob = params.get('rest_probability', 0.1)
    dur_pool = params.get('durations', DURATIONS)
    dur_weights_pool = params.get('dur_weights', DUR_WEIGHTS)
    total_bars = params.get('total_bars', 8)
    beats_per_bar = int(params.get('time_signature', '4/4').split('/')[0])
    lo = params.get('note_range_low', 48)
    hi = params.get('note_range_high', 84)
    vel = params.get('velocity', 80)

    full_scale = _scale_notes(root, scale_semitones, lo, hi)
    if not full_scale:
        return []
    beat_sec = 60.0 / bpm
    total_beats = total_bars * beats_per_bar

    notes = []
    cur_pitch = rng_obj.choice(full_scale[:max(1, len(full_scale)//2)])
    cur_beat = 0.0

    while cur_beat < total_beats - 0.01:
        dur = _pick_duration(rng_obj, dur_pool, dur_weights_pool, total_beats - cur_beat)
        if rng_obj.random() < rest_prob:
            cur_beat += dur
            continue

        candidates = [p for p in full_scale if abs(p - cur_pitch) <= max_int]
        if not candidates:
            candidates = full_scale
        weights = [_interval_weight(abs(p - cur_pitch)) * (0.7 if p == cur_pitch else 1.0) for p in candidates]
        nxt = rng_obj.choices(candidates, weights=weights, k=1)[0]
        start_sec = cur_beat * beat_sec
        end_sec = (cur_beat + dur) * beat_sec
        notes.append(pretty_midi.Note(velocity=vel, pitch=nxt, start=start_sec, end=end_sec))
        cur_pitch = nxt
        cur_beat += dur
    return notes

def gen_chord_melody(root, scale_semitones, params):
    rng_obj = _rng(params)
    bpm = params.get('bpm', 120)
    mode = params.get('scale', 'major')
    prog_name = params.get('progression', 'pop')
    chord_tone_bias = params.get('chord_tone_bias', 0.6)
    total_bars = params.get('total_bars', 8)
    beats_per_bar = int(params.get('time_signature', '4/4').split('/')[0])
    lo = params.get('note_range_low', 48)
    hi = params.get('note_range_high', 84)
    vel = params.get('velocity', 80)
    notes_per_chord = params.get('notes_per_chord', 2)

    mode_type = 'maj' if mode in ('major','pentatonic_major','lydian','mixolydian') else 'min'
    prog = PROGRESSIONS.get(prog_name, PROGRESSIONS['pop'])
    ct = CHORD_TONES[mode_type]

    beat_sec = 60.0 / bpm
    beats_per_chord = total_bars * beats_per_bar / max(1, len(prog) * notes_per_chord)
    beats_per_chord *= notes_per_chord
    full_scale = _scale_notes(root, scale_semitones, lo, hi)

    notes = []
    cur_beat = 0.0
    for _ in range(notes_per_chord * total_bars * beats_per_bar // int(beats_per_chord + 0.5) * notes_per_chord):
        if cur_beat >= total_bars * beats_per_bar:
            break
        chord_idx = int(cur_beat // beats_per_chord) % len(prog)
        roman = prog[chord_idx]
        tones = ct.get(roman, ct['I']) if mode_type == 'maj' else ct.get(roman, ct['i'])
        chord_pitches = []
        for t in tones:
            for oct_off in (-1, 0, 1):
                p = t + root + oct_off * 12
                if lo <= p <= hi:
                    chord_pitches.append(p)
        if not chord_pitches:
            chord_pitches = full_scale

        dur = _pick_duration(rng_obj, DURATIONS, DUR_WEIGHTS, total_bars * beats_per_bar - cur_beat)
        if rng_obj.random() < 0.05:
            cur_beat += dur
            continue
        if rng_obj.random() < chord_tone_bias:
            pitch = rng_obj.choice(chord_pitches)
        else:
            others = [p for p in full_scale if p not in chord_pitches]
            pitch = rng_obj.choice(others) if others else rng_obj.choice(chord_pitches)
        start_sec = cur_beat * beat_sec
        end_sec = (cur_beat + dur) * beat_sec
        notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=start_sec, end=end_sec))
        cur_beat += dur
    return notes

def gen_markov_melody(root, scale_semitones, params):
    rng_obj = _rng(params)
    bpm = params.get('bpm', 120)
    rest_prob = params.get('rest_probability', 0.08)
    total_bars = params.get('total_bars', 8)
    beats_per_bar = int(params.get('time_signature', '4/4').split('/')[0])
    lo = params.get('note_range_low', 48)
    hi = params.get('note_range_high', 84)
    vel = params.get('velocity', 80)

    matrix_var = params.get('markov_matrix', 'generic')
    mat = MARKOV_MATRICES.get(matrix_var, MARKOV_MATRICES['generic'])
    full_scale = _scale_notes(root, scale_semitones, lo, hi)
    if not full_scale:
        return []
    beat_sec = 60.0 / bpm
    total_beats = total_bars * beats_per_bar

    # Map scale degrees to actual pitches
    degree_pitches = {}
    for deg in range(7):
        semitone = scale_semitones[deg % len(scale_semitones)]
        candidates = [p for p in full_scale if (p - root) % 12 == semitone]
        degree_pitches[deg] = candidates if candidates else full_scale

    notes = []
    cur_deg = rng_obj.randint(0, 6)
    cur_beat = 0.0
    while cur_beat < total_beats - 0.01:
        dur = _pick_duration(rng_obj, DURATIONS, DUR_WEIGHTS, total_beats - cur_beat)
        if rng_obj.random() < rest_prob:
            cur_beat += dur
            continue
        # Pick next degree from Markov matrix
        row = mat[cur_deg]
        next_deg = rng_obj.choices(range(7), weights=row, k=1)[0]
        pitch = rng_obj.choice(degree_pitches[next_deg])
        start_sec = cur_beat * beat_sec
        end_sec = (cur_beat + dur) * beat_sec
        notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=start_sec, end=end_sec))
        cur_deg = next_deg
        cur_beat += dur
    return notes

def gen_contour_melody(root, scale_semitones, params):
    rng_obj = _rng(params)
    bpm = params.get('bpm', 120)
    total_bars = params.get('total_bars', 8)
    beats_per_bar = int(params.get('time_signature', '4/4').split('/')[0])
    lo = params.get('note_range_low', 48)
    hi = params.get('note_range_high', 84)
    vel = params.get('velocity', 80)
    climax_bar = params.get('climax_bar', int(total_bars * 0.6))
    cadence_rest = params.get('cadence_rest_prob', 0.1)

    full_scale = _scale_notes(root, scale_semitones, lo, hi)
    if not full_scale:
        return []
    mid_idx = len(full_scale) // 2
    beat_sec = 60.0 / bpm
    total_beats = total_bars * beats_per_bar

    # Build contour: start low-mid, rise to climax, fall to cadence
    def contour_pitch(beat):
        bar = beat / beats_per_bar
        if bar <= 1:
            t = bar / 1
            return int(mid_idx * (1 - t) + (mid_idx * 0.6) * t)  # start in lower half
        elif bar <= climax_bar:
            progress = (bar - 1) / (climax_bar - 1)
            # Rise toward upper range
            target = mid_idx + int((len(full_scale) - mid_idx - 1) * min(progress * 1.1, 1.0))
            cur = int(mid_idx * 0.6)
            return int(cur + (target - cur) * progress)
        else:
            # Fall to tonic area
            progress = (bar - climax_bar) / (total_bars - climax_bar)
            start_p = mid_idx + int((len(full_scale) - mid_idx - 1) * 0.6)
            end_p = int(mid_idx * 0.5)
            return int(start_p + (end_p - start_p) * min(progress, 1.0))

    notes = []
    cur_beat = 0.0
    while cur_beat < total_beats - 0.01:
        dur = _pick_duration(rng_obj, DURATIONS, DUR_WEIGHTS, total_beats - cur_beat)
        bar = cur_beat / beats_per_bar
        rest_p = cadence_rest if (total_bars - bar) < 2 else 0.05
        if rng_obj.random() < rest_p:
            cur_beat += dur
            continue
        cidx = contour_pitch(cur_beat)
        cidx = max(0, min(len(full_scale) - 1, cidx))
        # Add variation
        variation = rng_obj.randint(-2, 2)
        idx = max(0, min(len(full_scale) - 1, cidx + variation))
        pitch = full_scale[idx]
        start_sec = cur_beat * beat_sec
        end_sec = (cur_beat + dur) * beat_sec
        notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=start_sec, end=end_sec))
        cur_beat += dur
    return notes

def gen_combined(root, scale_semitones, params):
    out = []
    for gen_fn in (gen_scale_walk, gen_chord_melody, gen_markov_melody, gen_contour_melody):
        sub_params = dict(params)
        bars = params.get('total_bars', 8)
        sub_params['total_bars'] = max(2, bars // 2)
        sub_params['_seed'] = params.get('_seed', 0) + hash(gen_fn.__name__) % 2**31
        result = gen_fn(root, scale_semitones, sub_params)
        # Shift each sub-melody in time so they interlace
        offset = len(out) * 0.25
        for n in result:
            n.start += offset
            n.end += offset
        out.extend(result)
    out.sort(key=lambda n: n.start)
    return out[:200]  # cap

ALGORITHMS = {
    'scale_walk': {'fn': gen_scale_walk, 'label': 'Scale Walk', 'desc': 'Random walk within scale with weighted intervals'},
    'chord': {'fn': gen_chord_melody, 'label': 'Chord Progression', 'desc': 'Melody based on chord progression templates'},
    'markov': {'fn': gen_markov_melody, 'label': 'Markov Chain', 'desc': 'Scale degree transitions via Markov matrix'},
    'contour': {'fn': gen_contour_melody, 'label': 'Phrase Contour', 'desc': 'Phrase structure with rise-climax-fall contour'},
    'combined': {'fn': gen_combined, 'label': 'Combined', 'desc': 'All four algorithms interlaced'},
}

GENRE_INSTRUMENT_MAP = {
    'pop': 'piano', 'edm': 'synth_pad', 'rock': 'guitar',
    'blues': 'guitar', 'jazz': 'piano', 'classical': 'piano',
    'rap': 'bass', 'reggae': 'guitar',
}

ALGORITHM_DEFAULTS = {
    'scale_walk': {'max_interval': 7, 'rest_probability': 0.1, 'durations': DURATIONS, 'dur_weights': DUR_WEIGHTS},
    'chord': {'progression': 'pop', 'chord_tone_bias': 0.6, 'notes_per_chord': 2},
    'markov': {'markov_matrix': 'generic', 'rest_probability': 0.08},
    'contour': {'climax_bar': 5, 'cadence_rest_prob': 0.1},
    'combined': {},
}

def generate(params):
    algorithm = params.get('algorithm', 'scale_walk')
    key_name = params.get('key', 'C')
    scale_name = params.get('scale', 'major')
    root = NOTES.index(key_name)
    scale_semitones = SCALES.get(scale_name, SCALES['major'])
    gen_info = ALGORITHMS.get(algorithm, ALGORITHMS['scale_walk'])
    gen_fn = gen_info['fn']

    octave_base = params.get('octave_base')
    octave_offsets = params.get('octave_offsets', [])
    if octave_base is not None and isinstance(octave_offsets, list):
        oct_low = octave_base
        oct_high = octave_base
        for off in octave_offsets:
            if isinstance(off, (int, float)):
                if off < 0:
                    oct_low = min(oct_low, octave_base + int(off))
                elif off > 0:
                    oct_high = max(oct_high, octave_base + int(off))
        params['note_range_low'] = oct_low * 12 + root
        params['note_range_high'] = (oct_high + 1) * 12 - 1
    if '_seed' not in params:
        params['_seed'] = random.randint(0, 2**31)

    midi_notes = gen_fn(root, scale_semitones, params)
    if not midi_notes:
        return None

    note_offset = params.get('note_offset', 0)
    if note_offset:
        for n in midi_notes:
            n.pitch += note_offset

    bpm = params.get('bpm', 120)
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    program = 0
    instr = params.get('instrument', 'piano')
    for inst in INSTRUMENTS:
        if inst['name'] == instr:
            program = inst['id']
            break
    inst_obj = pretty_midi.Instrument(program=program)
    inst_obj.notes = midi_notes
    pm.instruments.append(inst_obj)
    return pm

DEFAULT_PARAMS = {
    'algorithm': 'scale_walk', 'key': 'C', 'scale': 'major',
    'bpm': 120, 'instrument': 'piano', 'time_signature': '4/4',
    'total_bars': 8, 'velocity': 80,
    'max_interval': 7, 'rest_probability': 0.1,
    'progression': 'pop', 'chord_tone_bias': 0.6, 'notes_per_chord': 2,
    'markov_matrix': 'generic',
    'climax_bar': 5, 'cadence_rest_prob': 0.1,
    'durations': DURATIONS, 'dur_weights': DUR_WEIGHTS,
    'octave_base': None, 'octave_offsets': [],
    'note_offset': 0,
}

def validate_params(p):
    out = dict(DEFAULT_PARAMS)
    for k, v in p.items():
        if k in out:
            out[k] = v
    out['_seed'] = p.get('_seed', random.randint(0, 2**31))
    return out
