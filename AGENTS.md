# Miskam'o — Personal Music Assistant

## Overview
Local personal music assistant. Includes a dataset generator (MIDI → distorted WAV pairs), a MIDI melody generator with multiple algorithms, and — as one of the options — voice-to-MIDI conversion using DDSP timbre transfer + pitch correction.

## Tech Stack
- **Backend**: FastAPI + Jinja2, Python 3.11, PyTorch (CUDA), CREPE + DDSP
- **Frontend**: Vanilla JS + Font Awesome 6.5.2, server-side FluidSynth audio rendering
- **Audio**: pyfluidsynth + FluidR3_GM.sf2 (148 MB), matplotlib + librosa for piano roll PNGs
- **MIDI**: pretty_midi, hmmlearn

## Commands
```bash
# Run server (GPU)
start_win_web_ui_gui.bat

start_win_web_ui_cpu.bat

python main.py

# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_midi_gen_algorithm.py -v

## Test commands (run only on request)
# %test                     — run all tests (python -m pytest tests/ -v)
# %test <context>            — run specific test(s) matching context
#   Examples:
#     %test midi utils       → python -m pytest tests/test_midi_utils.py -v
#     %test структуры проекта → python -m pytest tests/test_project_structure.py -v
#     %test midigen          → python -m pytest tests/test_api_midigen.py tests/test_midi_gen_algorithm.py tests/test_api_midigen_presets.py -v
#     %test i18n             → python -m pytest tests/test_i18n.py tests/test_template.py -v
#
# %test new <context>        — create new tests for the given feature
#   Examples:
#     %test new нового генератора  → create tests/test_new_generator.py
```

## Port
Server runs on **http://127.0.0.1:7890**

## Project Structure
```
├── main.py                 # FastAPI server (entry point)
├── core/                   # Framework + shared utilities
│   ├── app.py             # create_app() factory
│   ├── module_base.py     # ModuleMeta dataclass
│   ├── module_loader.py   # scans modules/
│   ├── settings_hub.py    # /api/core/settings
│   ├── config.py          # Paths, settings_cache
│   ├── fluidsynth.py      # SHARED: MIDI→WAV
│   ├── midi.py            # SHARED: _truncate_notes, _render_pianoroll, etc.  
│   ├── utils.py           # SHARED: _ensure_wav, _transliterate
│   ├── i18n.py            # T() with mtime auto-reload
│   ├── static/
│   │   ├── framework.js   # T(), toast(), TabManager
│   │   ├── framework.css  # CSS variables, card, btn
│   │   └── favicon.svg
│   └── templates/
│       └── base.html      # Shell template (module tabs rendered by JS)
├── modules/                # Independent modules (remove folder = remove module)
│   ├── audio_to_midi/     # Module: Audio→MIDI
│   │   ├── __init__.py    # ModuleMeta(id='audio-to-midi')
│   │   ├── audio2midi.py  # MiskamoEngine
│   │   └── tab-audio-to-midi.js
│   ├── midigen/           # Module: MIDI Generator
│   │   ├── __init__.py
│   │   ├── midi_gen.py    # 5 algorithms
│   │   └── tab-midigen.js
│   ├── dataset/           # Module: Dataset Generator
│   │   ├── __init__.py
│   │   └── tab-dataset.js
│   ├── history/           # Module: History
│   │   ├── __init__.py
│   │   ├── history.py     # _history_list, _uid_from_name
│   │   └── tab-history.js
│   ├── testing/           # Module: Tests UI
│   │   ├── __init__.py
│   │   └── tab-tests.js
│   └── train/             # Module: Train (stub)
│       ├── __init__.py
│       └── tab-train.js
├── templates/
│   └── index.html         # Legacy template (JS refs → modules/)
├── static/
│   └── tab-settings.js    # Framework settings (not a module)
├── lang/
│   ├── ru.json
│   └── en.json
├── _shared/               # Content dirs (_ prefix = interaction dirs)
│   ├── _output/
│   ├── _tmp/
│   ├── _midi_banks/
│   ├── _midi_gen_presets/
│   ├── _corrupt_presets/
│   ├── _dataset/
│   └── _train_output/
├── tests/                 # Unit tests (dev tool, not a module)
├── tests_e2e/             # E2E Playwright tests
├── DDSP-Timbre-Transfer/  # Git submodule
└── FluidR3_GM.sf2         # SoundFont (148 MB)

## Architecture & Key Conventions

### Tabs
HTML tabs: process, eval, history, midigen, dataset, train, tests, settings.
`rebuildTabs()` reads `localStorage['tab_order']` — order & visibility configurable in Settings.

### Internationalization (i18n)
- **Server-side**: `{{ T('key') }}` in Jinja2 → `core/i18n.py` reads `lang/*.json`
- **Client-side**: `T('key')` in JS → looks up `_T` dict rendered in template
- **Rule**: every `T('key')` used in static JS must have an entry in `var _T = {...}` in `index.html:600`
- `test_template.py` enforces: no missing `_T` keys, no dead keys, all keys exist in lang files

### Engine
- Lazy-loaded via `_get_engine()` (singleton, created on first request)
- Prevents 4x duplicate loading with uvicorn `reload=True`

### Settings
- `settings_cache` dict mutated in-place (`clear()` + `update()`) so `from core.config import settings_cache` references stay valid
- `set_lang()` bug fixed: was `save_settings(settings_cache)` which clears the same dict; now `save_settings(dict(settings_cache))`

### FluidSynth
- `FLUIDSYNTH_AUDIO_DRIVER=file` set before synth creation (prevents SDL3 warning)
- Global synth cached in `_get_synth()`
- Each render: `system_reset()` + `program_select()`

### Tests
- 146 tests, pass in ~3s
- `conftest.py` mocks `miskamo` (GPU model) and `core.fluidsynth` (native SF2) at module level
- `patch_paths` autouse fixture redirects all I/O to temp dir per test
- `httpx2` installed — suppresses StarletteDeprecationWarning

### MIDI Generation
5 algorithms: Scale Walk, Chord Progression, Markov Chain, Phrase Contour, Combined.
Seed determinism: same seed → same output. `-1` = random.
Key/Scale/Octave configured via toggle buttons (piano keyboard layout).

### Dataset Generation
MIDI → FluidSynth (piano) → per-note distortions (drift, jitter, bad notes, noise).
WAV pairs: `NNN_clean.wav` + `NNN_corrupt.wav`.
Split long MIDIs into `max_dur` segments.
Cancel via `_gen_cancel_flag` flag + dedicated endpoint.

## Critical Gotchas
- `asyncio.create_subprocess_exec` raises `NotImplementedError` on Windows → use `threading.Thread` + `subprocess.Popen` + `asyncio.Queue` for `/api/tests/run`
- `_gen_cancel_flag` is a module-level flag; `await asyncio.sleep(0)` yields to event loop for cancellation
- Preset filenames use transliteration (Cyrillic → Latin)
- Noise formula: `noise_std = (noise / 100.0) * 0.00254`
- **НИКОГДА не удалять SUMMARY.md** — только дополнять или редактировать. В нём вся история проекта.

## Module initialization convention
Каждый модуль при первом импорте (`__init__.py`) создаёт необходимые ему директории и файлы с проверкой `exist_ok=True`: если папка/файл уже существует — использует как есть, если нет — создаёт. Модуль **никогда не перезаписывает и не удаляет** чужие данные.
- **Framework** (`core/config.py`) создаёт только свои директории: `_output`, `_tmp`, `_midi_banks`
- **Модули** создают свои: `dataset` → `_dataset`, `_corrupt_presets`; `train` → `_train_output`; `midigen` → `_midi_gen_presets`

## Pitch Offsets (MIDI Generation & Piano Roll)

### Internal octave convention
Приложение использует собственное соглашение: **C{octave} = MIDI {octave×12}** (C4 = MIDI 48).
Стандарт MIDI: C4 = MIDI 60. Ableton: C3 = MIDI 60.

### `note_range_high` fix (`core/midi_gen.py:332`)
Было: `(oct_high+1)×12 + root − 1` — из-за `+root` уходило на октаву выше.
Стало: `(oct_high+1)×12 − 1` — высшая нота = B в самой высокой выбранной октаве.

### `note_offset` в генерации (`core/midi_gen.py`)
После генерации нот во внутреннем диапазоне применяется `note_offset`, сдвигающий все pitch:

| Режим | note_offset | MIDI-файл |
|-------|-------------|-----------|
| **По умолчанию** | +12 | Внутр.диапазон +12 → стандарт (C4=60) |
| **Ableton ON** | +24 | Внутр.диапазон +24 → Ableton (C3=60) |

### API generate → pianoroll (`main.py`)
В ответ эндпоинта `pitch_low/pitch_high` всегда содержат **baseline +12** (стандартная MIDI-конвенция).
Дополнительный сдвиг для Ableton передаётся как `note_offset`, который `_render_pianoroll()` вычитает из нот перед отрисовкой — так лейблы на пианоролле всегда показывают стандартные октавы.

### Плеер (`/api/midi/render`)
При Ableton ON JS добавляет `transpose=-12`, чтобы FluidSynth рендерил ноты на октаву ниже (звук совпадает с ожидаемым).

### Скачивание MIDI
При Ableton ON к имени файла добавляется `_a` перед расширением (`gen_..._a.mid`).

### Настройка
Чекбокс в Настройках → «Смещение MIDI для Ableton (C3 = Pitch 60)». Сохраняется в `settings.json` как `ableton: bool`.
При переключении — тост «Ableton смещение ВКЛ» (зелёный) / «Ableton смещение ВЫКЛ» (красный).

## GitHub — что на репозитории, что локально
- `_midi_banks/` — на GitHub только пустая `generated/.gitkeep`; все банки (maestro, testbank и т.д.) — локально
- `_corrupt_presets/` — на GitHub только `heavy.json`, `light.json`, `medium.json`; пользовательские и тестовые — локально
- `_midi_gen_presets/` — полностью локально, на GitHub не попадает
- `*.dll` — Windows-нативные библиотеки (`libfluidsynth*.dll`, `sndfile.dll`, `SDL3.dll`); не на GitHub, устанавливаются через `install_windows.bat` или Homebrew на macOS

## Файлы установки и запуска
- `install_windows.bat` — Windows: pip install + создание папок
- `install_macos.sh` — macOS: Homebrew + pip install + создание папок
- `start_win_web_ui_gui.bat` / `start_mac_web_ui_gui.sh` — запуск (GPU)
- `start_win_web_ui_cpu.bat` / `start_mac_web_ui_cpu.sh` — запуск (CPU, CUDA_VISIBLE_DEVICES=-1)
- `.sh` файлы имеют `+x` (chmod) — исполняемые

