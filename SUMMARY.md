# Miskam'o — Личный музыкальный помощник

## Обзор

Локальный (без облачных API) музыкальный помощник на Python.
Преобразует голос/напевку в MIDI через CREPE + DDSP, генерирует MIDI-мелодии по 5 алгоритмам,
создаёт датасеты MIDI→WAV (clean + corrupt) для обучения audio-to-audio моделей.

- **Порт:** http://127.0.0.1:7890
- **Язык:** русский, английский
- **Лицензия:** MIT

## Быстрый старт

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
start_win_web_ui_gui.bat   # GPU
start_win_web_ui_cpu.bat   # CPU
python main.py         # напрямую
```

**Требования:** Python 3.11+, NVIDIA GPU CUDA 12+ (рекомендуется) / CPU, FluidR3_GM.sf2 (148 МБ)

## Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Backend | FastAPI + Jinja2, Python 3.11 |
| ML | PyTorch 2.x (CUDA 12), CREPE + DDSP |
| Frontend | Vanilla JS, Font Awesome 6.5.2 |
| Аудио | pyfluidsynth + FluidR3_GM.sf2 (148 МБ), matplotlib + librosa (PNG) |
| MIDI | pretty_midi, hmmlearn |
| Тесты | pytest 9.0+, pytest-asyncio, httpx, httpx2 |
| E2E | Playwright (30 cursor + 3 tsig) |

## Структура проекта

```
├── main.py                 # FastAPI-сервер (все эндпоинты)
├── core/audio2midi.py       # MiskamoEngine (CREPE → DDSP → MIDI)
│
├── core/
│   ├── config.py           # Пути, settings_cache, save/load
│   ├── i18n.py             # T() с авто-перезагрузкой
│   ├── fluidsynth.py       # _get_synth(), _render_midi(), _notes_to_audio()
│   ├── midi.py             # _truncate_notes(), _split_into_segments(), _render_pianoroll()
│   ├── midi_gen.py         # generate() с 5 алгоритмами
│   ├── history.py          # _history_list(), _uid_from_name()
│   └── utils.py            # _ensure_wav(), _transliterate()
│
├── templates/
│   └── index.html          # Single-page UI (~1080 строк)
│
├── static/
│   ├── tab-audio-to-midi.js # Вкладка аудио→MIDI
│   ├── tab-dataset.js       # Вкладка датасета
│   ├── tab-history.js       # Вкладка истории
│   ├── tab-midigen.js       # Вкладка MIDI-генерации
│   ├── tab-settings.js      # Вкладка настроек
│   ├── tab-tests.js         # Вкладка тестов
│   └── tab-train.js         # Вкладка обучения (заглушка)
│
├── lang/
│   ├── ru.json              # 203 ключа (русский)
│   └── en.json              # 203 ключа (английский)
│
├── tests/
│   ├── conftest.py          # Моки + patch_paths autouse
│   └── test_*.py            # 14 файлов, 146 тестов
│
├── tests_e2e/
│   ├── conftest.py          # E2E моки + uvicorn-сервер
│   ├── test_cursor_e2e.py   # 30 тестов курсора
│   └── test_midigen_tsig_e2e.py # 3 теста time signature
│
├── _tmp/                    # Временные файлы
├── _output/                 # Сгенерированные WAV/MIDI
├── _midi_banks/             # MIDI-банки (maestro ~2000 MIDI)
├── _midi_gen_presets/       # Пресеты MIDI-генератора (JSON)
├── _corrupt_presets/        # Пресеты искажений датасета (JSON)
├── dataset/                 # Сгенерированные датасеты
├── train_output/            # Результаты обучения
├── DDSP-Timbre-Transfer/    # Подмодуль DDSP
├── FluidR3_GM.sf2           # SoundFont (148 МБ)
├── requirements.txt
├── requirements-test.txt
├── start_win_web_ui_gui.bat
├── start_win_web_ui_cpu.bat
├── settings.json
├── ratings.csv
```

## Вкладки

8 вкладок (порядок/видимость — `localStorage['tab_order']`):

| Вкладка | Назначение |
|---------|-----------|
| **process** (Аудио в MIDI) | Загрузка/запись WAV → CREPE+DDSP → MIDI |
| **eval** (Ручная оценка) | Оценка аудио по 10-балльной шкале |
| **history** (Мои генерации) | Просмотр, плеер, пианолла, скачивание, удаление |
| **midigen** (MIDI Ген) | 5 алгоритмов, пресеты, batch, предпросмотр |
| **dataset** (Датасет) | Clean/corrupt WAV-пары из MIDI-банков |
| **train** (Обучение) | Заглушка |
| **tests** (Тесты) | Запуск 146 тестов из UI |
| **settings** (Настройки) | Язык, инструмент, курсор, Ableton, вкладки |

## API-эндпоинты (FastAPI)

### Страницы
- `GET /` — главная HTML
- `GET /lang/{lang}` — смена языка

### Voice → MIDI
- `POST /api/process` — аудио → MIDI + обработанное аудио
- `GET /api/file/{name}` — скачивание из `_output/`
- `GET /api/midi/pianoroll` — PNG пианоллы (с опциональным `note_offset`)
- `GET /api/midi/render` — MIDI → WAV (с опциональным `transpose`)
- `GET /api/ratings` — оценки
- `POST /api/rate` — сохранить оценку

### MIDI Generation
- `GET /api/midi_gen/info` — алгоритмы, инструменты, гаммы, прогрессии
- `POST /api/midi_gen/generate` — генерация одной мелодии
- `POST /api/midi_gen/generate_batch` — массовая генерация
- `POST /api/midi_gen/save_to_bank` — сохранить в банк
- `GET /api/midi_gen/presets` — список пресетов
- `POST /api/midi_gen/presets/save` / `load` / `delete` / `rename` — CRUD

### Dataset
- `POST /api/dataset/generate` — SSE-поток генерации
- `POST /api/dataset/cancel` — отмена
- `GET /api/presets` — пресеты искажений

### Banks
- `GET /api/banks` — список банков
- `POST /api/banks/rename` / `delete` — управление
- `POST /api/save_bank` — выбор банка

### History
- `GET /api/history` — список (с пагинацией)
- `POST /api/history/delete` / `clear` — управление

### Settings / Tests
- `POST /api/settings` — сохранение настроек
- `POST /api/tests/run` — запуск pytest (SSE stream)

## Audio-to-MIDI Engine (core/audio2midi.py)

Класс `MiskamoEngine` — голос → инструмент (DDSP) → MIDI:
- **Загрузка:** DDSP-Timbre-Transfer, AutoEncoderWrapper, PyTorch (CUDA/CPU)
- **process(input, output_audio, output_midi, add_reverb)** — основной пайплайн
- **F0→MIDI:** медианный фильтр (5), hysteresis (30 центов), gap fill (0.04 с), min note (0.08 с), confidence (0.35)

## MIDI Generator (core/midi_gen.py)

### 5 алгоритмов
| Алгоритм | Суть |
|----------|------|
| Scale Walk | Random walk в гамме с взвешенными интервалами |
| Chord Progression | Мелодия по аккордовым шаблонам |
| Markov Chain | Переходы ступеней по матрице Маркова |
| Phrase Contour | Подъём → кульминация → спад |
| Combined | Все 4 с временным смещением |

### Параметры
- **Гаммы (12):** major, minor, pentatonic, blues, dorian, phrygian, lydian, mixolydian, locrian, chromatic
- **Прогрессии (8):** pop, edm, rock, blues_12, jazz, classical, rap, reggae
- **Инструменты (10):** piano, guitar, bass, violin, trumpet, sax, flute, vibraphone, synth_pad, drums
- Seed-детерминизм: `-1` = случайный
- Клавиши, октавы — toggle buttons
- BPM (40–200), такты (2–32), размерность (2/4, 3/4, 4/4, 6/8, 7/8)
- Громкость нот: velocity 80

### Pitch Offsets (MIDI Generation & Piano Roll)

**Внутреннее соглашение:** C{octave} = MIDI {octave×12} (C4 = MIDI 48).
Стандарт: C4 = MIDI 60. Ableton: C3 = MIDI 60.

**`note_range_high` (`midi_gen.py:332`):**
- Было: `(oct_high+1)×12 + root − 1` — уходило на октаву выше
- Стало: `(oct_high+1)×12 − 1` — высшая нота = B в верхней октаве

**`note_offset` в генерации:**

| Режим | note_offset | MIDI-файл |
|-------|-------------|-----------|
| По умолчанию | +12 | внутр.диапазон +12 → стандарт (C4=60) |
| Ableton ON | +24 | внутр.диапазон +24 → Ableton (C3=60) |

**API generate → pianoroll:** `pitch_low/pitch_high` всегда baseline +12.
Дополнительный сдвиг Ableton передаётся как `note_offset`, который `_render_pianoroll()` вычитает из нот — лейблы всегда в стандарте.

**Плеер:** при Ableton ON JS добавляет `transpose=-12` — звук в плеере совпадает с ожидаемым.

**Скачивание:** при Ableton ON `_a` в имени файла.

**Настройка:** чекбокс в Настройках → «Смещение MIDI для Ableton (C3 = Pitch 60)».
Тосты: зелёный «Ableton смещение ВКЛ» / красный «Ableton смещение ВЫКЛ».

## Dataset Generator

MIDI → FluidSynth (piano) → понотные искажения → WAV-пары.

**Типы искажений:**
- **Pitch drift** — смещение высоты (σ полутонов/100)
- **Timing jitter** — сдвиг start/end (σ мс)
- **Bad notes** — замена ноты шумом (%)
- **Noise** — белый шум (SNR ~57dB при 100%)
- **Split** — разрезание длинных MIDI на сегменты

**Формат:** `NNN_clean.wav` + `NNN_corrupt.wav` + `_params.json`
**Формула шума:** `noise_std = (noise / 100.0) * 0.00254`
**Отмена:** `_gen_cancel_flag` + `/api/dataset/cancel`

## FluidSynth (core/fluidsynth.py)

- `FLUIDSYNTH_AUDIO_DRIVER=file` перед созданием
- Глобальный `_get_synth()` с кэшированием
- Каждый рендер: `system_reset()` + `program_select()`
- Стерео → моно, нормализация peak → 0.9

## Интернационализация

- **Сервер:** `core/i18n.py`, `T(key)` с авто-перезагрузкой по mtime
- **Клиент:** `_T = {...}` в `index.html:943`, JS `T(k)`
- **Правило:** каждый `T('key')` в JS должен быть в `_T` (проверяется тестом)
- **lang/ru.json, en.json** — по 203 ключа

## Настройки (settings.json)

```python
language, midi_bank, confirm_delete, toast_sec, clear_tmp,
default_instrument, cursor_size, cursor_enabled, cursor_shape,
cursor_angle, cursor_rotation, cursor_rotation_reverse, cursor_rotation_speed,
cursor_shadow, cursor_shadow_length, ableton
```

`settings_cache` мутируется in-place. Сохранение: `save_settings(dict(settings_cache))`.

## Тесты

### Unit-тесты — 146 тестов (~3 с)

| Файл | Тестов | Что тестирует |
|------|--------|--------------|
| `test_i18n.py` | 7 | lang-ключи, T() fallback |
| `test_config.py` | 11 | Settings roundtrip, defaults, banks, cache |
| `test_api_settings.py` | 7 | POST settings, lang, persistence |
| `test_api_process.py` | 7 | Process, file serving, ratings, MIDI |
| `test_api_midigen.py` | 13 | Generate, batch, save, seed determinism |
| `test_api_midigen_presets.py` | 12 | Presets CRUD |
| `test_api_dataset.py` | 8 | Dataset SSE, cancel, split |
| `test_api_banks.py` | 6 | Banks list, rename, delete |
| `test_api_history.py` | 5 | History list, pagination, delete |
| `test_midi_utils.py` | 13 | Note truncation, segment split |
| `test_midi_gen_algorithm.py` | 18 | 5 алгоритмов, seed, validate_params |
| `test_utils.py` | 19 | Transliteration, UID, timestamps |
| `test_template.py` | 5 | _T keys, lang coverage |

### E2E-тесты — 33 теста (Playwright)

| Файл | Тестов | Что тестирует |
|------|--------|--------------|
| `test_cursor_e2e.py` | 30 | Курсор: формы, размер, вращение, след |
| `test_midigen_tsig_e2e.py` | 3 | Time signature radio buttons |

### Архитектура тестирования
- `conftest.py` мокает `miskamo` (GPU) и `core.fluidsynth` (SF2) на уровне модуля
- `patch_paths` autouse — перенаправляет I/O в temp
- E2E: поднимает настоящий uvicorn на свободном порту, Playwright Chromium headless

## Критические моменты

1. **Windows + subprocess:** `asyncio.create_subprocess_exec` → `NotImplementedError`; используем `threading.Thread` + `subprocess.Popen` + `asyncio.Queue` для `/api/tests/run`
2. **Флаг отмены:** `_gen_cancel_flag` — модульный; `await asyncio.sleep(0)` для yield event loop
3. **Транслитерация:** кириллица в именах пресетов → латиница
4. **SUMMARY.md:** **НИКОГДА НЕ УДАЛЯТЬ** — только дополнять или редактировать. В нём вся история проекта.
5. **FluidSynth:** `FLUIDSYNTH_AUDIO_DRIVER=file` обязателен до создания синтезатора
6. **DDSP:** `DDSP-Timbre-Transfer/` добавляется в `sys.path` внутри `core/audio2midi.py`
