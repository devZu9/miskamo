"""
Miskam'o — Web UI (Gradio)
Личный музыкальный помощник: голос → MIDI, генератор, датасет, обучение
"""

import os, sys, json, csv, asyncio
from pathlib import Path
import gradio as gr
import torch
import numpy as np
import soundfile as sf
import pretty_midi

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from miskamo import MiskamoEngine

SETTINGS_FILE = ROOT / "settings.json"
RATINGS_FILE  = ROOT / "ratings.csv"
DATASET_DIR   = ROOT / "dataset"
TRAIN_DIR     = ROOT / "train_output"
MIDI_BANKS    = ROOT / "midi_banks"
DATASET_DIR.mkdir(exist_ok=True)
TRAIN_DIR.mkdir(exist_ok=True)

# ─── i18n ─────────────────────────────────────────────────────────

L10N = {
    "ru": {
        "title": "Miskam'o",
        "desc": "Загрузите напевку, получите MIDI + аудио инструмента",
        "tab_process":    "Обработка",
        "tab_evaluate":   "Оценка",
        "tab_dataset":    "Датасет",
        "tab_train":      "Обучение",
        "tab_settings":   "Настройки",
        "upload_audio":   "Загрузить WAV (голос / напевка)",
        "reverb":         "Реверберация",
        "btn_process":    "Обработать → MIDI",
        "out_audio":      "Аудио инструмента",
        "out_midi":       "Скачать MIDI",
        "status_ready":   "Готово",
        "listen":         "Прослушать результат",
        "rating":         "Оценка",
        "note_optional":  "Заметка",
        "btn_rate":       "Сохранить оценку",
        "ratings_log":    "Журнал оценок",
        "bank_selector":  "MIDI-банк",
        "refresh_banks":  "Обновить",
        "corruption":     "Параметры искажений",
        "pitch_drift":    "Дрейф высоты",
        "timing_jitter":  "Джиттер тайминга",
        "bad_notes":      "Плохие ноты",
        "vibrato_rate":   "Частота вибрато",
        "vibrato_depth":  "Глубина вибрато",
        "noise_db":       "Шум",
        "max_dur":        "Длительность",
        "btn_generate":   "Сгенерировать датасет",
        "dataset_log":    "Лог генерации",
        "lr":             "Скорость обучения",
        "epochs":         "Эпохи",
        "btn_train":      "Начать обучение",
        "train_log":      "Лог обучения",
        "language":       "Язык",
        "btn_save":       "Сохранить",
        "settings_saved": "Настройки сохранены. Перезапустите приложение.",
        "choose_lang":    "Выберите язык",
        "restart_msg":    "Настройки сохранены. Закройте и откройте приложение снова.",
        "no_midi":        "MIDI не найдены",
        "generated_n":    "Сгенерировано пар",
        "saved_rating":   "Сохранено: оценка",
        "train_soon":     "Обучение скоро появится",
        "loading":        "Загрузка модели...",
        "process_hint":   "Поддерживаются WAV, MP3, FLAC. Длительность до 30 секунд.",
        "bank_info":      "Файлов в банке",
    },
    "en": {
        "title": "Miskam'o",
        "desc": "Upload a vocal recording, get MIDI + instrument audio",
        "tab_process":    "Process",
        "tab_evaluate":   "Evaluate",
        "tab_dataset":    "Dataset",
        "tab_train":      "Train",
        "tab_settings":   "Settings",
        "upload_audio":   "Upload WAV (voice / humming)",
        "reverb":         "Reverb",
        "btn_process":    "Process → MIDI",
        "out_audio":      "Instrument audio",
        "out_midi":       "Download MIDI",
        "status_ready":   "Done",
        "listen":         "Listen to result",
        "rating":         "Rating",
        "note_optional":  "Note",
        "btn_rate":       "Save rating",
        "ratings_log":    "Ratings log",
        "bank_selector":  "MIDI bank",
        "refresh_banks":  "Refresh",
        "corruption":     "Corruption parameters",
        "pitch_drift":    "Pitch drift",
        "timing_jitter":  "Timing jitter",
        "bad_notes":      "Bad notes",
        "vibrato_rate":   "Vibrato rate",
        "vibrato_depth":  "Vibrato depth",
        "noise_db":       "Noise",
        "max_dur":        "Duration",
        "btn_generate":   "Generate dataset",
        "dataset_log":    "Generation log",
        "lr":             "Learning rate",
        "epochs":         "Epochs",
        "btn_train":      "Start training",
        "train_log":      "Training log",
        "language":       "Language",
        "btn_save":       "Save",
        "settings_saved": "Settings saved. Restart the app.",
        "choose_lang":    "Choose language",
        "restart_msg":    "Settings saved. Close and reopen the app.",
        "no_midi":        "No MIDI found",
        "generated_n":    "Generated pairs",
        "saved_rating":   "Saved: rating",
        "train_soon":     "Training coming soon",
        "loading":        "Loading model...",
        "process_hint":   "WAV, MP3, FLAC supported. Max 30 seconds.",
        "bank_info":      "Files in bank",
    },
}

# ─── Settings ─────────────────────────────────────────────────────

def load_settings():
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {"language": "ru", "midi_bank": "maestro"}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

settings = load_settings()
LANG = settings.get("language", "ru")

def _(key):
    return L10N.get(LANG, L10N["ru"]).get(key, key)

def get_midi_banks():
    banks = []
    if MIDI_BANKS.exists():
        for d in sorted(MIDI_BANKS.iterdir()):
            if d.is_dir():
                c = len(list(d.rglob("*.mid*")))
                if c > 0:
                    banks.append((f"{d.name}  ({c} {_('bank_info').split()[0]})", d.name, c))
    return banks

# ─── Pre-load engine at startup ───────────────────────────────────

print(f"[Miskam'o] {_('loading')}", end=" ", flush=True)
_engine = MiskamoEngine(instrument="sax")
print(f"[OK] ({_('status_ready')})")

# ─── Tab: Process ─────────────────────────────────────────────────

def process_audio(audio_path, add_reverb, progress=gr.Progress()):
    if audio_path is None:
        return None, None, _("upload_audio")
    try:
        progress(0.3, desc="Extracting pitch...")
        midi_path = str(ROOT / "_temp_out.mid")
        audio_out = str(ROOT / "_temp_out.wav")
        progress(0.5, desc="Synthesizing instrument...")
        _engine.process(audio_path, output_audio=audio_out, output_midi=midi_path, add_reverb=add_reverb)
        progress(1.0, desc=_("status_ready"))
        return audio_out, midi_path, _("status_ready")
    except Exception as e:
        return None, None, f"Error: {e}"

# ─── Tab: Evaluate ────────────────────────────────────────────────

def load_ratings():
    if not RATINGS_FILE.exists():
        return ""
    with open(RATINGS_FILE) as f:
        return f.read()

def save_rating(audio_path, rating, note=""):
    if audio_path is None:
        return _("saved_rating")
    with open(RATINGS_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["audio", "rating", "note", "version"])
        w.writerow([audio_path, rating, note, "miskamo_v1"])
    return f"{_('saved_rating')}: {rating}/10\n\n{load_ratings()}"

# ─── Tab: Dataset ─────────────────────────────────────────────────

def refresh_banks_ui():
    banks = get_midi_banks()
    if not banks:
        return gr.Dropdown(choices=[], value=None, label=_("bank_selector"), allow_custom_value=True)

    choices = [(b[0], b[1]) for b in banks]
    vals = [b[1] for b in banks]
    s = load_settings()
    val = s.get("midi_bank") if s.get("midi_bank") in vals else vals[0]
    return gr.Dropdown(choices=choices, value=val, label=_("bank_selector"), allow_custom_value=True)

def generate_dataset(bank_val, pitch_drift, timing_jitter, bad_notes,
                     vibrato_rate, vibrato_depth, noise_db, max_dur,
                     progress=gr.Progress()):
    bank_dir = MIDI_BANKS / bank_val
    if not bank_dir.exists():
        return f"{_('no_midi')}: {bank_val}"

    files = sorted(bank_dir.rglob("*.mid*"))
    if not files:
        return f"{_('no_midi')}: {bank_val}"

    out_dir = DATASET_DIR / f"{bank_val}_p{pitch_drift}_j{timing_jitter}_b{bad_notes}"
    out_dir.mkdir(parents=True, exist_ok=True)

    sr = 16000
    count = 0
    for i, fpath in enumerate(files[:300]):
        progress((i+1)/min(len(files),300), desc=f"{i+1}/{min(len(files),300)}")
        try:
            midi_data = pretty_midi.PrettyMIDI(str(fpath))
            if not midi_data.instruments:
                continue
            inst = midi_data.instruments[0]
            if inst.is_drum and len(midi_data.instruments) > 1:
                inst = midi_data.instruments[1]
            notes = inst.notes
            if len(notes) < 4:
                continue

            end_t = min(midi_data.get_end_time(), max_dur)
            total = int(end_t * sr)
            if total <= 0:
                continue
            audio = np.zeros(total)

            for n in notes:
                start_s = n.start
                end_s = min(n.end, max_dur)
                if end_s <= start_s:
                    continue
                freq = 440.0 * (2.0 ** ((n.pitch - 69) / 12.0))
                drift = np.random.normal(0, pitch_drift / 100.0)
                freq = freq * (2.0 ** drift)

                s = max(0, int(start_s * sr))
                e = min(total, int(end_s * sr))
                length = e - s
                if length <= 0:
                    continue
                t = np.arange(length) / sr
                jit = int(np.random.normal(0, timing_jitter / 1000.0 * sr))
                s = max(0, min(total - 1, s + jit))
                e = min(total, s + length)
                if e <= s:
                    continue
                length = e - s
                t = np.arange(length) / sr
                vib = vibrato_depth / 100.0 * np.sin(2 * np.pi * vibrato_rate * t)
                sig = np.sin(2 * np.pi * freq * (1 + vib) * t)

                if np.random.random() < bad_notes / 100.0:
                    sig = np.random.uniform(-0.3, 0.3, len(t))

                fade = np.minimum(np.arange(length) / (sr * 0.01), 1.0)[::-1]
                fade = np.minimum(fade, np.arange(length) / (sr * 0.01))
                audio[s:e] += sig * fade * 0.3

            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio / peak * 0.9
            if noise_db < 40:
                noise = np.random.randn(total) * (10 ** (-noise_db / 20))
                audio = audio + noise
                audio = audio / (np.max(np.abs(audio)) + 1e-8) * 0.9

            base = fpath.stem
            sf.write(str(out_dir / f"{base}_corrupt.wav"), audio, sr)
            midi_data.write(str(out_dir / f"{base}_original.mid"))
            count += 1
        except Exception:
            continue

    return f"{_('generated_n')}: {count}  →  {out_dir.name}"

# ─── Tab: Train ───────────────────────────────────────────────────

def do_train(lr, epochs):
    return _("train_soon")

# ─── Tab: Settings ────────────────────────────────────────────────

def save_settings_ui(lang, bank_val):
    save_settings({"language": lang, "midi_bank": bank_val})
    return _("settings_saved")

# ─── Custom CSS ───────────────────────────────────────────────────

CUSTOM_CSS = """
:root {
  --primary: #8b5cf6;
  --primary-hover: #7c3aed;
  --bg-dark: #0f0f1a;
  --bg-card: #1a1a2e;
  --bg-input: #16213e;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --border: #2d2d4a;
  --success: #22c55e;
}
body { background: var(--bg-dark) !important; }
.gradio-container { background: transparent !important; max-width: 1200px !important; margin: 0 auto !important; }
.app-header { text-align: center; padding: 2rem 0 1rem 0; }
.app-header h1 { font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #d946ef); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
.app-header p { color: var(--text-muted); margin: 0.5rem 0 0 0; font-size: 0.95rem; }
.tabs { border: none !important; }
.tabs button { background: var(--bg-card) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: 8px 8px 0 0 !important; padding: 0.65rem 1.2rem !important; font-size: 0.9rem !important; }
.tabs button.selected { background: var(--primary) !important; border-color: var(--primary) !important; }
.tab-nav { gap: 4px !important; }
.card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }
label { color: var(--text-muted) !important; font-size: 0.85rem !important; font-weight: 500 !important; }
input, select, textarea { background: var(--bg-input) !important; border-color: var(--border) !important; color: var(--text) !important; border-radius: 8px !important; }
button.primary { background: linear-gradient(135deg, var(--primary), #d946ef) !important; border: none !important; border-radius: 8px !important; color: white !important; font-weight: 600 !important; padding: 0.6rem 1.5rem !important; }
button.primary:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(139, 92, 246, 0.4); }
.slider-container { margin: 0.5rem 0; }
audio { border-radius: 8px; width: 100%; }
footer { display: none !important; }
.status-ok { color: var(--success) !important; font-weight: 500; }
"""

# ─── Build UI ─────────────────────────────────────────────────────

def create_ui():
    with gr.Blocks(
        title=_("title"),
        analytics_enabled=False,
    ) as app:
        # Header
        gr.HTML(f"""
        <div class="app-header">
            <h1>🎵 {_('title')}</h1>
            <p>{_('desc')}</p>
        </div>
        """)

        # Tabs
        with gr.Tabs(elem_classes="tabs"):
            # ── Tab 1: Process ──
            with gr.TabItem(f"🎧  {_('tab_process')}"):
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            audio_in = gr.Audio(
                                label=_("upload_audio"),
                                type="filepath",
                                format="wav",
                            )
                            gr.Markdown(f"<small style='color:var(--text-muted)'>{_('process_hint')}</small>")
                            with gr.Row():
                                reverb = gr.Checkbox(label=_("reverb"), value=True)
                            btn_process = gr.Button(_("btn_process"), variant="primary", size="lg")
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            audio_out = gr.Audio(label=_("out_audio"), type="filepath")
                            midi_out = gr.File(label=_("out_midi"))
                            status = gr.Textbox(label=_("tab_process"), elem_classes="status-ok")

                btn_process.click(
                    process_audio,
                    [audio_in, reverb],
                    [audio_out, midi_out, status],
                )

            # ── Tab 2: Evaluate ──
            with gr.TabItem(f"⭐  {_('tab_evaluate')}"):
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            eval_audio = gr.Audio(label=_("listen"), type="filepath")
                            rating = gr.Slider(1, 10, value=5, step=1, label=_("rating"))
                            eval_note = gr.Textbox(label=_("note_optional"), placeholder="...")
                            btn_rate = gr.Button(_("btn_rate"), variant="primary")
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            ratings_log = gr.Textbox(label=_("ratings_log"), lines=18)

                btn_rate.click(save_rating, [eval_audio, rating, eval_note], ratings_log)
                app.load(load_ratings, None, ratings_log)

            # ── Tab 3: Dataset ──
            with gr.TabItem(f"📊  {_('tab_dataset')}"):
                banks = get_midi_banks()
                bank_choices = [(b[0], b[1]) for b in banks] if banks else []
                bank_values = [b[1] for b in banks] if banks else []
                current_bank = settings.get("midi_bank") if settings.get("midi_bank") in bank_values else (bank_values[0] if bank_values else None)

                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            bank_dd = gr.Dropdown(
                                choices=bank_choices,
                                value=current_bank,
                                label=_("bank_selector"),
                                allow_custom_value=True,
                            )
                            btn_refresh = gr.Button(_("refresh_banks"), size="sm")
                            gr.Markdown(f"<small style='color:var(--text-muted)'>{MIDI_BANKS}</small>")

                        with gr.Group(elem_classes="card"):
                            gr.Markdown(f"### {_('corruption')}")
                            pitch_drift = gr.Slider(0, 200, value=30, step=5, label=_("pitch_drift"))
                            timing_jitter = gr.Slider(0, 500, value=50, step=10, label=_("timing_jitter"))
                            bad_notes = gr.Slider(0, 50, value=10, step=5, label=_("bad_notes"))
                            vibrato_rate = gr.Slider(0, 10, value=5, step=0.5, label=_("vibrato_rate"))
                            vibrato_depth = gr.Slider(0, 100, value=20, step=5, label=_("vibrato_depth"))
                            noise_db = gr.Slider(0, 40, value=20, step=5, label=_("noise_db"))
                            max_dur = gr.Slider(2, 30, value=10, step=1, label=_("max_dur"))
                            btn_gen = gr.Button(_("btn_generate"), variant="primary")
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            dataset_log = gr.Textbox(label=_("dataset_log"), lines=22)

                btn_refresh.click(refresh_banks_ui, None, bank_dd)
                btn_gen.click(
                    generate_dataset,
                    [bank_dd, pitch_drift, timing_jitter, bad_notes,
                     vibrato_rate, vibrato_depth, noise_db, max_dur],
                    dataset_log,
                )

            # ── Tab 4: Train ──
            with gr.TabItem(f"🎯  {_('tab_train')}"):
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            lr = gr.Number(label=_("lr"), value=0.0001)
                            epochs = gr.Number(label=_("epochs"), value=100)
                            btn_train = gr.Button(_("btn_train"), variant="primary")
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes="card"):
                            train_log = gr.Textbox(label=_("train_log"), lines=18)

                btn_train.click(do_train, [lr, epochs], train_log)

            # ── Tab 5: Settings ──
            with gr.TabItem(f"⚙  {_('tab_settings')}"):
                with gr.Column():
                    with gr.Group(elem_classes="card"):
                        lang_dd = gr.Dropdown(
                            choices=[("Русский", "ru"), ("English", "en")],
                            value=settings.get("language", "ru"),
                            label=_("language"),
                        )
                        banks_s = get_midi_banks()
                        bank_choices_s = [(b[0], b[1]) for b in banks_s] if banks_s else []
                        bank_values_s = [b[1] for b in banks_s] if banks_s else []
                        bank_s_dd = gr.Dropdown(
                            choices=bank_choices_s,
                            value=settings.get("midi_bank") if settings.get("midi_bank") in bank_values_s else (bank_values_s[0] if bank_values_s else None),
                            label=_("bank_selector"),
                            allow_custom_value=True,
                        )
                        btn_save = gr.Button(_("btn_save"), variant="primary")
                        save_msg = gr.Textbox(label="", lines=2)

                btn_save.click(save_settings_ui, [lang_dd, bank_s_dd], save_msg)

        return app

# ─── First launch language picker ──────────────────────────────────

def first_launch_ui():
    with gr.Blocks(
        title="Miskam'o",
        analytics_enabled=False,
    ) as app:
        gr.HTML("""
        <div class="app-header">
            <h1>Miskam'o</h1>
        </div>
        """)
        with gr.Column():
            with gr.Group(elem_classes="card"):
                gr.Markdown(f"## {_('choose_lang')}")
                lang_dd = gr.Dropdown(
                    choices=[("Русский", "ru"), ("English", "en")],
                    value="ru",
                    label=_("language"),
                    allow_custom_value=True,
                )
                btn = gr.Button(_("restart_msg").split(".")[0], variant="primary")
                msg = gr.Textbox(label="", lines=2)

        def save_first(lang):
            save_settings({"language": lang, "midi_bank": "maestro"})
            return _("restart_msg")

        btn.click(save_first, [lang_dd], msg)
        return app

# ─── Launch ────────────────────────────────────────────────────────

if __name__ == "__main__":
    s = load_settings()
    if s.get("language") not in ("ru", "en"):
        ui = first_launch_ui()
    else:
        ui = create_ui()
    theme = gr.themes.Base(
        primary_hue="violet",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    )
    ui.launch(server_name="127.0.0.1", server_port=7890, inbrowser=True,
              theme=theme, css=CUSTOM_CSS)
