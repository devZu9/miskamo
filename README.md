# Miskam'o

> Личный музыкальный помощник. Локально, без облачных API.

---

## Возможности

- **🎤 Voice → MIDI** *(опция)* — запись с микрофона или загрузка WAV; CREPE + DDSP → чистый MIDI
- **🎹 MIDI Generator** — 5 алгоритмов (Scale Walk, Chord, Markov, Contour, Combined), тональность/гамма/октава/BPM, массовая генерация
- **📊 Dataset Generator** — MIDI → искажённые WAV-пары (clean + corrupt) для обучения моделей audio-to-audio
- **📜 History** — просмотр, прослушивание, пианолла обработанных файлов
- **🧪 Tests** — запуск 146 тестов прямо из UI
- **🌐 i18n** — русский / английский (с авто-перезагрузкой переводов)

---

## Быстрый старт

### Требования

- Python 3.11+
- NVIDIA GPU с CUDA 12+ (рекомендуется) или CPU
- [FluidR3_GM.sf2](https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.sf2) (148 MB) — положить в корень проекта

### Установка

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt   # для тестов
```

### Запуск

```bash
# GPU (по умолчанию)
start_web_ui_gui.bat

# CPU
start_web_ui_cpu.bat

# Или напрямую:
python main.py
```

Открыть в браузере: **http://127.0.0.1:7890**

---

## Структура

| Путь | Назначение |
|------|-----------|
| Путь | Назначение |
|------|-----------|
| `main.py` | FastAPI-сервер (порт 7890) |
| `miskamo.py` | MiskamoEngine — CREPE → DDSP → MIDI |
| `core/config.py` | Настройки приложения |
| `core/i18n.py` | Интернационализация |
| `core/fluidsynth.py` | FluidSynth-рендеринг MIDI → WAV |
| `core/midi_gen.py` | Генерация MIDI-мелодий |
| `templates/index.html` | UI (single-page) |
| `static/tab-*.js` | JS по вкладкам |
| `lang/*.json` | Переводы (RU/EN) |
| `_midi_banks/` | MIDI-банки (maestro, testbank) |
| `_output/` | Результаты обработки |
| `_tmp/` | Временные файлы |

---

## Настройки

- **Язык**: выбор при первом запуске, смена в любой момент
- **Default instrument**: инструмент для превью Voice→MIDI (по умолч. саксофон)
- **Toast duration**: 3–15 сек
- **Порядок вкладок**: drag-to-reorder в Settings
- **Очистка `_tmp/`**: при запуске (опционально)

---

## Тесты

```bash
python -m pytest tests/ -v
# 146 тестов, ~3 секунды
```

---

## Форматы данных

- **Аудио на входе**: WAV (16-bit, 44100 Hz)
- **MIDI на выходе**: стандартный `.midi`
- **Датасет**: WAV-пары `NNN_clean.wav` / `NNN_corrupt.wav` + `_params.json`
- **Пресеты**: JSON-файлы с параметрами искажений/генерации

---

## Зависимости

- PyTorch 2.x + CUDA 12
- torchcrepe, hmmlearn, pretty_midi
- FastAPI + Jinja2 + uvicorn
- pyfluidsynth + FluidR3_GM.sf2
- matplotlib + librosa (пианолла)
- pytest + httpx + httpx2 (тесты)

---

## Лицензия

MIT
