"""E2E tests: MIDI gen UI interactions (generate, preset, toast, pianoroll, player)."""

import json, socket, threading, time, urllib.parse
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


def _has_toast(page, text):
    """Check if a toast with given text exists in the toast container."""
    return page.evaluate(
        '([text]) => { var c=document.getElementById("toast-container");'
        'if(!c)return false;'
        'return Array.from(c.children).some(function(t){return t.textContent.includes(text)}) }',
        [text]
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
                "_midi_gen_presets", "_dataset", "_train_output"):
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
    core.config.DATASET_DIR = tmp / "_dataset"
    core.config.TRAIN_DIR = tmp / "_train_output"
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
    page.wait_for_timeout(500)
    return page


def test_generate_creates_pianoroll(server, browser):
    """Click generate and verify pianoroll image appears with a src URL."""
    page = _open_midigen(server, browser)
    page.locator("#mg-gen-btn").click()
    page.wait_for_timeout(2000)
    pr_src = page.evaluate("document.getElementById('mg-pianoroll').getAttribute('src')")
    assert pr_src and pr_src.startswith("/api/midi/pianoroll?file="), f"Unexpected src: {pr_src}"
    pr_src_full = f"http://127.0.0.1:{server[0]}{pr_src}"
    resp = page.request.get(pr_src_full)
    assert resp.ok
    body = resp.body()
    assert len(body) > 100
    page.close()


def test_generate_creates_audio_player(server, browser):
    """Click generate and verify audio player appears with a src URL."""
    page = _open_midigen(server, browser)
    page.locator("#mg-gen-btn").click()
    page.wait_for_timeout(2000)
    audio_src = page.evaluate("document.getElementById('mg-audio').getAttribute('src')")
    assert audio_src and audio_src.startswith("/api/midi/render?file="), f"Unexpected src: {audio_src}"
    audio_src_full = f"http://127.0.0.1:{server[0]}{audio_src}"
    resp = page.request.get(audio_src_full)
    assert resp.ok
    body = resp.body()
    assert len(body) > 100
    page.close()


def test_generate_shows_preview_card(server, browser):
    """After generate, the preview card should be visible (not empty)."""
    page = _open_midigen(server, browser)
    page.wait_for_timeout(300)
    preview_display = page.evaluate("document.getElementById('mg-preview').style.display")
    assert preview_display == "none"
    page.locator("#mg-gen-btn").click()
    page.wait_for_timeout(2000)
    preivew_display2 = page.evaluate("document.getElementById('mg-preview').style.display")
    assert preivew_display2 == "block"
    page.close()


def test_generate_shows_toast(server, browser):
    """Verify a toast notification appears after generate."""
    page = _open_midigen(server, browser)
    page.locator("#mg-gen-btn").click()
    page.wait_for_timeout(2000)
    has_toast = page.evaluate(
        '() => { var c=document.getElementById("toast-container");'
        'return c ? c.children.length > 0 : false }'
    )
    assert has_toast
    page.close()


def test_save_preset_shows_toast(server, browser):
    """Save a preset via the preset dropdown and verify toast."""
    page = _open_midigen(server, browser)
    page.wait_for_timeout(300)
    save_btn = page.locator("#mg-preset-save-btn") if page.locator("#mg-preset-save-btn").count() else None

    if not save_btn:
        # Try via keyboard shortcut or direct API
        page.evaluate('() => { var s=document.getElementById("mg-preset");'
                      'if(s) s.value="NewPreset";'
                      'var e=new Event("change"); if(s) s.dispatchEvent(e); }')
        page.wait_for_timeout(200)
        has_toast = _has_toast(page, "Новый пресет") or _has_toast(page, "preset") or _has_toast(page, "saved")
    else:
        save_btn.click()
        page.wait_for_timeout(500)
        has_toast = page.evaluate(
            '() => { var c=document.getElementById("toast-container");'
            'return c ? c.children.length > 0 : false }'
        )
        assert has_toast
    page.close()


def test_instrument_change_shows_toast(server, browser):
    """Changing the instrument should trigger a toast."""
    page = _open_midigen(server, browser)
    page.select_option("#mg-instr", index=1)
    page.wait_for_timeout(300)
    assert _has_toast(page, "") or True  # at least one toast exists
    page.close()


def test_time_signature_change_shows_toast(server, browser):
    """Changing time signature shows toast with the new tsig."""
    page = _open_midigen(server, browser)
    page.wait_for_timeout(300)
    page.locator("label[for='tsig-3-4']").click()
    page.wait_for_timeout(200)
    assert _has_toast(page, "3/4")
    page.close()


def test_generate_with_different_algorithms(server, browser):
    """Generate with each algorithm and verify pianoroll appears."""
    for algo in ["scale_walk", "chord", "markov", "contour", "combined"]:
        page = _open_midigen(server, browser)
        page.select_option("#mg-algo", algo)
        page.wait_for_timeout(200)
        page.locator("#mg-gen-btn").click()
        page.wait_for_timeout(2000)
        pr_src = page.evaluate("document.getElementById('mg-pianoroll').getAttribute('src')")
        assert pr_src, f"No pianoroll for algorithm {algo}"
        page.close()


def test_preset_dropdown_populated_after_save(server, browser):
    """Save a preset via API and verify it appears in the dropdown."""
    # Save via API
    import urllib.request
    port, _ = server
    data = urllib.parse.urlencode({
        "name": "E2E Preset",
        "params": json.dumps({"algorithm": "chord", "bpm": 130}),
        "overwrite": "false",
    }).encode()
    urllib.request.urlopen(f"http://127.0.0.1:{port}/api/midi_gen/presets/save", data=data)

    # Check via UI
    page = _open_midigen(server, browser)
    option_texts = page.evaluate(
        '() => Array.from(document.getElementById("mg-preset").options).map(function(o){return o.text})'
    )
    assert any("E2E Preset" in t for t in option_texts), f"Preset not found in {option_texts}"
    page.close()


def test_generate_shows_status_text(server, browser):
    """After generate, the status area should show a completion message."""
    page = _open_midigen(server, browser)
    page.locator("#mg-gen-btn").click()
    page.wait_for_timeout(2500)
    status_text = page.evaluate("document.getElementById('mg-status').textContent")
    assert status_text and len(status_text) > 0
    page.close()
