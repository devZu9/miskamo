# Tests for Miskam'o

## Setup

```bash
pip install pytest pytest-asyncio httpx
```

## Running

```bash
# From project root:
python -m pytest tests/ -v

# Run with coverage:
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=term-missing

# Run specific file:
python -m pytest tests/test_midi_gen_algorithm.py -v

# Run specific test:
python -m pytest tests/test_midi_gen_algorithm.py::test_seed_determinism -v
```

## What's tested

| File | What |
|------|------|
| `test_i18n.py` | All 183 keys in both `lang/*.json`, `T()` fallback |
| `test_config.py` | Settings load/save roundtrip, defaults, bank discovery, cache mutation |
| `test_api_settings.py` | `POST /api/settings`, `GET /lang/{lang}`, persistence |
| `test_api_process.py` | `POST /api/process`, file serving, ratings, MIDI render/pianoroll |
| `test_api_midigen.py` | Generate, batch, save_to_bank, seed determinism, all algorithms |
| `test_api_midigen_presets.py` | MIDI gen presets: full CRUD + edge cases |
| `test_api_dataset.py` | Dataset SSE stream, cancel, split, params.json |
| `test_api_banks.py` | Banks list, rename (incl. Cyrillic), delete |
| `test_api_history.py` | History list, pagination, delete, clear |
| `test_midi_utils.py` | `_truncate_notes`, `_extract_segment`, `_split_into_segments` |
| `test_midi_gen_algorithm.py` | All 5 algorithms, seed determinism, `validate_params`, edge cases |
| `test_utils.py` | `_transliterate`, `_uid_from_name`, `_parse_ts`, `_ensure_wav` |

## Architecture

- `conftest.py` mocks `miskamo` and `core.fluidsynth` at module level (before importing `main`)
- `patch_paths` autouse fixture redirects all file I/O to a temp dir per test
- `seed_midi`/`seed_wav`/`seed_bank` fixtures create test artifacts
