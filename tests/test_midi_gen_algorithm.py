"""Test core.midi_gen algorithmic logic: seed determinism, all algorithms, edge cases."""

import pretty_midi
from core.midi_gen import generate, validate_params, DEFAULT_PARAMS


def _params(**kw):
    p = dict(DEFAULT_PARAMS)
    p.update(kw)
    return p


def test_generate_returns_pretty_midi():
    p = _params(algorithm="scale_walk", _seed=42)
    pm = generate(p)
    assert isinstance(pm, pretty_midi.PrettyMIDI)
    assert len(pm.instruments) >= 1


def test_all_algorithms_produce_notes():
    for algo in ["scale_walk", "chord", "markov", "contour", "combined"]:
        p = _params(algorithm=algo, _seed=42, total_bars=8)
        pm = generate(p)
        assert pm is not None, f"Algorithm {algo} returned None"
        notes = sum(len(i.notes) for i in pm.instruments)
        assert notes > 0, f"Algorithm {algo} produced 0 notes"


def test_seed_determinism():
    p1 = _params(algorithm="scale_walk", _seed=123, total_bars=8)
    p2 = _params(algorithm="scale_walk", _seed=123, total_bars=8)
    pm1 = generate(p1)
    pm2 = generate(p2)
    n1 = [(n.pitch, n.start, n.end, n.velocity) for i in pm1.instruments for n in i.notes]
    n2 = [(n.pitch, n.start, n.end, n.velocity) for i in pm2.instruments for n in i.notes]
    assert n1 == n2


def test_different_seeds_different_notes():
    p1 = _params(algorithm="chord", _seed=100, total_bars=8)
    p2 = _params(algorithm="chord", _seed=200, total_bars=8)
    pm1 = generate(p1)
    pm2 = generate(p2)
    n1 = [(n.pitch, n.start) for i in pm1.instruments for n in i.notes]
    n2 = [(n.pitch, n.start) for i in pm2.instruments for n in i.notes]
    assert n1 != n2


def test_instrument_program_set():
    p = _params(algorithm="scale_walk", instrument="sax", _seed=42)
    pm = generate(p)
    assert pm.instruments[0].program == 65  # sax


def test_validate_params_defaults():
    p = validate_params({})
    assert p["algorithm"] == "scale_walk"
    assert p["bpm"] == 120
    assert "_seed" in p


def test_validate_params_overrides():
    p = validate_params({"algorithm": "chord", "bpm": 200})
    assert p["algorithm"] == "chord"
    assert p["bpm"] == 200


def test_validate_params_strips_unknown():
    p = validate_params({"algorithm": "markov", "nonexistent_key": "value"})
    assert "nonexistent_key" not in p


def test_scale_notes_produces_range():
    from core.midi_gen import _scale_notes
    notes = _scale_notes(0, [0, 2, 4, 5, 7, 9, 11], 48, 72)
    assert all(48 <= n <= 72 for n in notes)
    assert len(notes) > 0


def test_rng_with_seed():
    from core.midi_gen import _rng
    r1 = _rng({"_seed": 42})
    r2 = _rng({"_seed": 42})
    assert r1.random() == r2.random()


def test_pick_duration():
    from core.midi_gen import _pick_duration
    from core.midi_gen import DURATIONS, DUR_WEIGHTS
    r = __import__("random").Random(42)
    d = _pick_duration(r, DURATIONS, DUR_WEIGHTS, 3.0)
    assert d in DURATIONS or d <= 3.0


def test_generate_with_custom_octave():
    p = _params(algorithm="scale_walk", _seed=42, total_bars=4,
                octave_base=3, octave_offsets=[-1])
    pm = generate(p)
    # Notes should be in lower range
    notes = [n.pitch for i in pm.instruments for n in i.notes]
    if notes:
        assert all(0 <= n <= 127 for n in notes)


def test_generate_with_high_octave():
    p = _params(algorithm="scale_walk", _seed=42, total_bars=4,
                octave_base=6, octave_offsets=[1, 2])
    pm = generate(p)
    notes = [n.pitch for i in pm.instruments for n in i.notes]
    if notes:
        assert all(n <= 127 for n in notes)


def test_generate_contour_specific_params():
    p = _params(algorithm="contour", _seed=42, total_bars=8,
                climax_bar=3, cadence_rest_prob=0.5)
    pm = generate(p)
    assert pm is not None


def test_generate_markov_with_different_matrix():
    p = _params(algorithm="markov", _seed=42, markov_matrix="generic")
    pm = generate(p)
    assert pm is not None


def test_chord_progression_variations():
    for prog in ["pop", "rock", "blues_12", "jazz", "classical", "rap", "reggae"]:
        p = _params(algorithm="chord", _seed=42, progression=prog, total_bars=8)
        pm = generate(p)
        assert pm is not None, f"Progression {prog} failed"
