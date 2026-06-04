"""End-to-end tests: custom cursor checkbox chain via Playwright."""

import os
import sys
import json
import time
import socket
import threading
from pathlib import Path
import tempfile
import shutil

import pytest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _has_class(sel, cls, page):
    return page.evaluate(
        '([sel, cls]) => { var e=document.querySelector(sel); return e ? e.classList.contains(cls) : false }',
        [sel, cls]
    )


def _get_style(sel, page):
    return page.evaluate(
        '([sel]) => { var e=document.querySelector(sel); return e ? e.getAttribute("style") || "" : "" }',
        [sel]
    )


def _get_display(sel, page):
    return page.evaluate(
        '([sel]) => { var e=document.querySelector(sel); return e ? getComputedStyle(e).display : "none" }',
        [sel]
    )


def _get_attr(sel, attr, page):
    return page.evaluate(
        '([sel, attr]) => { var e=document.querySelector(sel); return e ? e.getAttribute(attr) : null }',
        [sel, attr]
    )


def _is_checked(sel, page):
    return page.evaluate(
        '([sel]) => { var e=document.querySelector(sel); return e ? e.checked : false }',
        [sel]
    )


def _is_disabled(sel, page):
    return page.evaluate(
        '([sel]) => { var e=document.querySelector(sel); return e ? e.disabled : false }',
        [sel]
    )


def _body_has_class(cls, page):
    return page.evaluate(
        '([cls]) => document.body.classList.contains(cls)',
        [cls]
    )


def _get_css_prop(sel, prop, page):
    return page.evaluate(
        '([sel, prop]) => { var e=document.querySelector(sel); return e ? getComputedStyle(e).getPropertyValue(prop) : "" }',
        [sel, prop]
    )

def _trail_dot_count(page):
    return page.evaluate('() => document.getElementById("cursor-trail").childElementCount')

def _trail_dots_visible(page):
    """Count of trail dots that have display != 'none'."""
    return page.evaluate("""() => { var c=document.getElementById("cursor-trail"); if(!c)return 0; var n=0; for(var i=0;i<c.children.length;i++){if(c.children[i].style.display!=='none')n++} return n }""")


def _get_svg_transform(sel, page):
    return page.evaluate(
        '([sel]) => { var e=document.querySelector(sel); return e ? e.style.getPropertyValue("--cursor-duration") || "" : "" }',
        [sel]
    )


def _get_angle_style(page):
    """Return the text content of the cursor-spin-style element."""
    return page.evaluate(
        '() => { var s=document.getElementById("cursor-spin-style"); return s ? s.textContent : "" }'
    )


def _run_server(port):
    import uvicorn
    config = uvicorn.Config(
        "main:app", host="127.0.0.1", port=port,
        log_level="warning", reload=False,
        env_file=None,
    )
    config.load()
    server = uvicorn.Server(config=config)
    server.run()


@pytest.fixture(scope="module")
def server():
    tmp = Path(tempfile.mkdtemp(prefix="miskamo_e2e_"))
    tmp_settings = tmp / "settings.json"
    tmp_settings.write_text(json.dumps({
        "language": "ru", "midi_bank": "",
 "confirm_delete": True,
        "toast_sec": 6, "clear_tmp": True, "default_instrument": "sax",
        "cursor_size": 24, "cursor_enabled": False, "cursor_shape": "triangle",
        "cursor_angle": 0, "cursor_rotation": False, "cursor_rotation_reverse": False, "cursor_rotation_speed": 5,
        "cursor_shadow": True, "cursor_shadow_length": 10,
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
    for attr, pname in [("OUTPUT_DIR","OUTPUT_DIR"), ("TMP_DIR","TMP_DIR"),
                        ("MIDI_BANKS","MIDI_BANKS"),
                        ("CORRUPT_PRESETS_DIR","CORRUPT_PRESETS_DIR"),
                        ("_MIDI_GEN_PRESETS_DIR","MIDI_GEN_PRESETS_DIR")]:
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


def _open_settings(server, browser):
    port, _ = server
    page = browser.new_page()
    page.goto(f"http://127.0.0.1:{port}")
    page.wait_for_load_state("networkidle")
    page.locator(".tab-settings").click()
    page.wait_for_timeout(400)
    return page


def _reset_settings(port):
    """POST default cursor settings to the API."""
    import urllib.request
    import urllib.parse
    post_data = urllib.parse.urlencode({
        "lang": "ru", "midi_bank": "",
        "confirm_delete": "true", "toast_sec": 6, "clear_tmp": "true",
        "default_instrument": "sax",
        "cursor_size": 24, "cursor_enabled": "false", "cursor_shape": "triangle",
        "cursor_angle": 0, "cursor_rotation": "false", "cursor_rotation_reverse": "false", "cursor_rotation_speed": 5,
        "cursor_shadow": "true", "cursor_shadow_length": 10,
    }).encode()
    urllib.request.urlopen(f"http://127.0.0.1:{port}/api/settings", data=post_data)


# ─────────────────────────────────────────────────────────────────
# Initial state
# ─────────────────────────────────────────────────────────────────

def test_initial_cursor_hidden(server, browser):
    page = _open_settings(server, browser)
    assert _get_display("#cursor-dot", page) == "none"
    page.close()


def test_initial_body_no_cursor_none(server, browser):
    page = _open_settings(server, browser)
    assert _body_has_class("cursor-none", page) is False
    page.close()


def test_initial_checkbox_unchecked(server, browser):
    page = _open_settings(server, browser)
    assert _is_checked("#settings-cursor-enable", page) is False
    page.close()


def test_initial_body_dimmed(server, browser):
    """Cursor settings body starts dimmed when cursor is off."""
    page = _open_settings(server, browser)
    assert _has_class("#cursor-settings-body", "dimmed", page)
    page.close()


def test_initial_shape_triangle_checked(server, browser):
    """Default shape is triangle (radio checked)."""
    page = _open_settings(server, browser)
    assert _is_checked("#cs-triangle", page) is True
    page.close()


def test_initial_rotation_off(server, browser):
    page = _open_settings(server, browser)
    assert _is_checked("#settings-cursor-rotation", page) is False
    page.close()


def test_initial_trail_on(server, browser):
    page = _open_settings(server, browser)
    assert _is_checked("#settings-cursor-shadow", page) is True
    page.close()


# ─────────────────────────────────────────────────────────────────
# Enabling cursor
# ─────────────────────────────────────────────────────────────────

def test_enable_shows_svg(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _get_display("#cursor-dot", page) != "none"
    page.close()


def test_enable_undims_body(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-settings-body", "dimmed", page) is False
    page.close()


def test_enable_adds_cursor_none(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _body_has_class("cursor-none", page) is True
    page.close()


def test_enable_mousemove_updates_position(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.mouse.move(300, 200)
    page.wait_for_timeout(50)
    s = _get_style("#cursor-dot", page)
    assert "300" in s or "200" in s
    page.close()


def test_enable_shows_trail(server, browser):
    page = _open_settings(server, browser)
    if _get_display("#cursor-trail", page) != "none":
        page.locator("#settings-cursor-enable").uncheck()
        page.wait_for_timeout(200)
    assert _get_display("#cursor-trail", page) == "none"

    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _get_display("#cursor-trail", page) != "none"
    page.close()


def test_enable_persists_after_reload(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(400)

    page.reload()
    page.wait_for_load_state("networkidle")
    page.locator(".tab-settings").click()
    page.wait_for_timeout(400)

    assert _is_checked("#settings-cursor-enable", page) is True
    assert _get_display("#cursor-dot", page) != "none"
    page.close()


def test_enable_writes_settings_json(server, browser):
    """Verify settings.json on disk has cursor_enabled=true."""
    port, tmp = server
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(1500)

    sf = tmp / "settings.json"
    data = json.loads(sf.read_text(encoding="utf-8"))
    assert data.get("cursor_enabled") is True
    assert data.get("cursor_size") == 24

    _reset_settings(port)
    page.close()


# ─────────────────────────────────────────────────────────────────
# Disabling cursor
# ─────────────────────────────────────────────────────────────────

def test_disable_hides_svg(server, browser):
    page = _open_settings(server, browser)
    cb = page.locator("#settings-cursor-enable")
    cb.check()
    page.wait_for_timeout(100)
    cb.uncheck()
    page.wait_for_timeout(100)
    assert _get_display("#cursor-dot", page) == "none"
    page.close()


def test_disable_dims_body(server, browser):
    page = _open_settings(server, browser)
    cb = page.locator("#settings-cursor-enable")
    cb.check()
    page.wait_for_timeout(100)
    cb.uncheck()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-settings-body", "dimmed", page)
    page.close()


def test_disable_removes_cursor_none(server, browser):
    page = _open_settings(server, browser)
    cb = page.locator("#settings-cursor-enable")
    cb.check()
    page.wait_for_timeout(100)
    cb.uncheck()
    page.wait_for_timeout(100)
    assert _body_has_class("cursor-none", page) is False
    page.close()


def test_disable_hides_trail(server, browser):
    page = _open_settings(server, browser)
    cb = page.locator("#settings-cursor-enable")
    cb.check()
    page.wait_for_timeout(100)
    cb.uncheck()
    page.wait_for_timeout(100)
    assert _get_display("#cursor-trail", page) == "none"
    page.close()


# ─────────────────────────────────────────────────────────────────
# Shape changes via radio buttons
# ─────────────────────────────────────────────────────────────────

def test_shape_triangle_shows_path(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _is_checked("#cs-triangle", page) is True
    # Enable rotation so triangle spins
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    d = _get_attr("#cursor-shape-el", "d", page)
    assert d, "path d should exist"
    assert "Z" in d
    assert _has_class("#cursor-dot", "spinning", page)
    page.close()


def test_shape_square_shows_path(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    page.locator("label[for='cs-square']").click()
    page.wait_for_timeout(100)
    d = _get_attr("#cursor-shape-el", "d", page)
    assert d, "path d should exist"
    assert "L" in d
    assert "Z" in d
    assert _has_class("#cursor-dot", "spinning", page)
    page.close()


def test_shape_circle_shows_path(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    page.locator("label[for='cs-circle']").click()
    page.wait_for_timeout(100)
    d = _get_attr("#cursor-shape-el", "d", page)
    assert d, "path d should exist"
    assert "C" in d
    assert "Z" in d
    assert not _has_class("#cursor-dot", "spinning", page)
    page.close()


def test_shape_triangle_no_spin_without_rotation(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert not _has_class("#cursor-dot", "spinning", page)
    page.close()


def test_shape_square_no_spin_without_rotation(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("label[for='cs-square']").click()
    page.wait_for_timeout(100)
    assert not _has_class("#cursor-dot", "spinning", page)
    page.close()


# ─────────────────────────────────────────────────────────────────
# Size slider
# ─────────────────────────────────────────────────────────────────

def test_size_slider_updates_svg(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor").fill("48")
    page.wait_for_timeout(100)
    s = _get_style("#cursor-dot", page)
    assert "width: 48px" in s
    page.close()


def test_size_slider_persists(server, browser):
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor").fill("48")
    page.wait_for_timeout(400)

    page.reload()
    page.wait_for_load_state("networkidle")
    page.locator(".tab-settings").click()
    page.wait_for_timeout(400)

    val = page.evaluate("document.getElementById('settings-cursor').value")
    assert val == "48"
    page.close()


# ─────────────────────────────────────────────────────────────────
# Rotation toggle
# ─────────────────────────────────────────────────────────────────

def test_rotation_toggle_spinning(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert not _has_class("#cursor-dot", "spinning", page)
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-dot", "spinning", page)
    page.locator("#settings-cursor-rotation").uncheck()
    page.wait_for_timeout(100)
    assert not _has_class("#cursor-dot", "spinning", page)
    page.close()


def test_rotation_speed_changes_duration(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation-speed").fill("2")
    page.wait_for_timeout(100)
    dur = _get_css_prop("#cursor-dot", "--cursor-duration", page)
    # Speed 2 → ~12.56s
    assert "12" in dur
    page.close()


def test_rotation_speed_row_dimmed_when_rotation_off(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-speed-row", "dimmed", page) is True
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-speed-row", "dimmed", page) is False
    page.locator("#settings-cursor-rotation").uncheck()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-speed-row", "dimmed", page) is True
    page.close()


# ─────────────────────────────────────────────────────────────────
# Reverse rotation
# ─────────────────────────────────────────────────────────────────

def test_reverse_rotation_toggle(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    # Without reverse: keyframes go +360
    style = page.evaluate(
        '() => { var s=document.getElementById("cursor-spin-style"); return s ? s.textContent : "" }'
    )
    assert "rotate(0deg)}to" in style  # 0 → 360
    # Enable reverse
    page.locator("#settings-cursor-rotation-reverse").check()
    page.wait_for_timeout(100)
    style = page.evaluate(
        '() => { var s=document.getElementById("cursor-spin-style"); return s ? s.textContent : "" }'
    )
    assert "rotate(-360deg)" in style  # 0 → -360
    page.close()


# ─────────────────────────────────────────────────────────────────
# Angle slider
# ─────────────────────────────────────────────────────────────────

def test_angle_slider_applies_static_rotation(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    # Default angle 0 → CSS var is 0deg
    ang = _get_css_prop("#cursor-dot", "--cursor-angle", page)
    assert "0deg" in ang or ang == ""
    # Set angle to 45
    page.locator("#settings-cursor-angle").fill("45")
    page.wait_for_timeout(100)
    ang = _get_css_prop("#cursor-dot", "--cursor-angle", page)
    assert "45deg" in ang
    # Keyframes also updated (for spinning)
    key = _get_angle_style(page)
    assert "rotate(45deg)" in key and "rotate(405deg)" in key  # 45 → 45+360
    page.close()


def test_angle_row_dimmed_for_circle(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-angle-row", "dimmed", page) is False
    page.locator("label[for='cs-circle']").click()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-angle-row", "dimmed", page) is True
    page.locator("label[for='cs-triangle']").click()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-angle-row", "dimmed", page) is False
    page.close()


# ─────────────────────────────────────────────────────────────────
# Shadow toggle
# ─────────────────────────────────────────────────────────────────

def test_trail_toggle_hides_shows_dots(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    # Trail starts ON by default → dots visible
    assert _trail_dots_visible(page) == 10
    page.locator("#settings-cursor-shadow").uncheck()
    page.wait_for_timeout(100)
    assert _trail_dots_visible(page) == 1  # one center dot stays
    page.locator("#settings-cursor-shadow").check()
    page.wait_for_timeout(100)
    assert _trail_dots_visible(page) == 10
    page.close()


def test_trail_length_changes_dot_count(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    # Default length 10 → 10 dots
    assert _trail_dot_count(page) == 10
    page.locator("#settings-cursor-shadow-length").fill("7")
    page.wait_for_timeout(100)
    assert _trail_dot_count(page) == 7
    page.close()


def test_trail_length_row_dimmed_when_trail_off(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    # Trail starts ON → row NOT dimmed
    assert _has_class("#cursor-shadow-length-row", "dimmed", page) is False
    page.locator("#settings-cursor-shadow").uncheck()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-shadow-length-row", "dimmed", page) is True
    page.locator("#settings-cursor-shadow").check()
    page.wait_for_timeout(100)
    assert _has_class("#cursor-shadow-length-row", "dimmed", page) is False
    page.close()


# ─────────────────────────────────────────────────────────────────
# Persistence of new settings
# ─────────────────────────────────────────────────────────────────

def test_new_settings_persist_after_reload(server, browser):
    port, _ = server
    _reset_settings(port)
    page = _open_settings(server, browser)
    page.locator("#settings-cursor-enable").check()
    page.wait_for_timeout(100)
    page.locator("label[for='cs-square']").click()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-angle").fill("45")
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation-speed").fill("8")
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-rotation-reverse").check()
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-shadow-length").fill("12")
    page.wait_for_timeout(100)
    page.locator("#settings-cursor-shadow").uncheck()
    page.wait_for_timeout(1000)

    page.reload()
    page.wait_for_load_state("networkidle")
    page.locator(".tab-settings").click()
    page.wait_for_timeout(400)

    assert _is_checked("#cs-square", page) is True
    assert _is_checked("#settings-cursor-rotation", page) is True
    assert _is_checked("#settings-cursor-rotation-reverse", page) is True
    assert _is_checked("#settings-cursor-shadow", page) is False
    val = page.evaluate("document.getElementById('settings-cursor-angle').value")
    assert val == "45"
    page.close()
