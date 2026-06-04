"""End-to-end tests: MIDI gen time signature radio persistence."""

import json, socket, threading, time
from pathlib import Path
import tempfile, shutil
import pytest
from playwright.sync_api import sync_playwright


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _is_checked(sel, page):
    return page.evaluate(
        '([sel]) => { var e=document.querySelector(sel); return e ? e.checked : false }',
        [sel]
    )


def _run_server(port):
    import uvicorn
    config = uvicorn.Config(
        "main:app", host="127.0.0.1", port=port,
        log_level="warning", reload=False, env_file=None,
    )
    config.load()
    uvicorn.Server(config=config).run()


@pytest.fixture(scope="module")
def server():
    tmp = Path(tempfile.mkdtemp(prefix="miskamo_e2e_"))
    tmp_settings = tmp / "settings.json"
    tmp_settings.write_text(json.dumps({
        "language": "ru", "midi_bank": "", "confirm_delete": True,
        "toast_sec": 6, "clear_tmp": True, "default_instrument": "piano",
        "cursor_size": 24, "cursor_enabled": False, "cursor_shape": "triangle",
        "cursor_angle": 0, "cursor_rotation": False, "cursor_rotation_reverse": False,
        "cursor_rotation_speed": 5, "cursor_shadow": True, "cursor_shadow_length": 10,
    }), encoding="utf-8")

    for sub in ("_output", "_tmp", "_midi_banks", "_corrupt_presets",
                "_midi_gen_presets", "dataset", "train_output"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)

    import core.config
    monkey = {}
    for attr in ("OUTPUT_DIR", "TMP_DIR", "MIDI_BANKS",
                 "CORRUPT_PRESETS_DIR", "MIDI_GEN_PRESETS_DIR",
                 "DATASET_DIR", "TRAIN_DIR", "SETTINGS_FILE"):
        monkey[attr] = getattr(core.config, attr)

    core.config.OUTPUT_DIR = tmp / "_output"
    core.config.TMP_DIR = tmp / "_tmp"
    core.config.MIDI_BANKS = tmp / "_midi_banks"
    core.config.CORRUPT_PRESETS_DIR = tmp / "_corrupt_presets"
    core.config.MIDI_GEN_PRESETS_DIR = tmp / "_midi_gen_presets"
    core.config.DATASET_DIR = tmp / "dataset"
    core.config.TRAIN_DIR = tmp / "train_output"
    core.config.SETTINGS_FILE = tmp / "settings.json"

    import main as m
    for attr, pname in [("OUTPUT_DIR", "OUTPUT_DIR"), ("TMP_DIR", "TMP_DIR"),
                        ("MIDI_BANKS", "MIDI_BANKS"),
                        ("CORRUPT_PRESETS_DIR", "CORRUPT_PRESETS_DIR"),
                        ("_MIDI_GEN_PRESETS_DIR", "MIDI_GEN_PRESETS_DIR")]:
        setattr(m, attr, getattr(core.config, pname))

    core.config.load_settings()

    port = _free_port()

    t = threading.Thread(target=_run_server, args=(port,), daemon=True)
    t.start()

    import urllib.request
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError("Server did not start")

    yield port, tmp

    for attr, orig in monkey.items():
        setattr(core.config, attr, orig)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


def _open_midigen(server, browser):
    port, _ = server
    page = browser.new_page()
    page.goto(f"http://127.0.0.1:{port}")
    page.wait_for_load_state("networkidle")
    page.locator('.tab[data-tab="midigen"]').click()
    page.wait_for_timeout(400)
    return page


def test_tsig_default_is_4_4(server, browser):
    page = _open_midigen(server, browser)
    assert _is_checked("#tsig-4-4", page) is True
    val = page.evaluate("document.getElementById('mg-tsig').value")
    assert val == "4/4"
    page.close()


def test_tsig_radio_persistence(server, browser):
    page = _open_midigen(server, browser)

    assert _is_checked("#tsig-4-4", page) is True

    page.locator("label[for='tsig-3-4']").click()
    page.wait_for_timeout(100)
    assert _is_checked("#tsig-3-4", page) is True
    assert _is_checked("#tsig-4-4", page) is False

    page.reload()
    page.wait_for_load_state("networkidle")
    page.locator('.tab[data-tab="midigen"]').click()
    page.wait_for_timeout(400)

    assert _is_checked("#tsig-3-4", page) is True
    assert _is_checked("#tsig-4-4", page) is False
    page.close()


def test_tsig_all_values_sync_hidden_select(server, browser):
    page = _open_midigen(server, browser)

    pairs = [("2/4", "tsig-2-4"), ("3/4", "tsig-3-4"),
             ("4/4", "tsig-4-4"), ("6/8", "tsig-6-8"), ("7/8", "tsig-7-8")]
    for tsig, radio_id in pairs:
        page.locator("label[for='" + radio_id + "']").click()
        page.wait_for_timeout(100)
        assert _is_checked("#" + radio_id, page) is True
        val = page.evaluate("document.getElementById('mg-tsig').value")
        assert val == tsig

    page.close()
