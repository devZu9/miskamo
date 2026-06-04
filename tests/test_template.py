"""Test that every T('key') call in JS has its key in the _T dictionary."""

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "index.html"
STATIC_DIR = ROOT / "static"
LANG_DIR = ROOT / "lang"

# JS files that use T()
JS_FILES = sorted(STATIC_DIR.glob("tab-*.js"))


def _T_keys():
    """Return set of all keys in the template's var _T = { ... } dict."""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'var _T\s*=\s*\{(.*?)\};', html, re.DOTALL)
    assert m, "var _T not found in template"
    return set(re.findall(r'(\w+)\s*:\s*"', m.group(1)))


def _js_T_calls(text):
    """Find all T('key') or T(\"key\") literal string calls."""
    return set(re.findall(r"""T\('([^']+)'\)|T\("([^"]+)"\)""", text))


def _all_js_T_keys():
    """Return set of all keys used in T('...') across template JS + static JS files."""
    keys = set()
    html = TEMPLATE.read_text(encoding="utf-8")
    # Strip Jinja2 {{ }} blocks — those are server-rendered, not JS T() calls
    js_only = re.sub(r"\{\{.*?\}\}", "", html)
    for match in _js_T_calls(js_only):
        keys.add(match[0] or match[1])
    for fp in JS_FILES:
        text = fp.read_text(encoding="utf-8")
        for match in _js_T_calls(text):
            keys.add(match[0] or match[1])
    return keys


def _all_lang_keys():
    """All keys present in both lang files."""
    keys = set()
    for fp in sorted(LANG_DIR.glob("*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        keys.update(data.keys())
    return keys


# ── Tests ─────────────────────────────────────────────────────

def test_all_js_T_calls_have_key_in_T():
    """Every T('key') in index.html and tab-*.js must be in _T dict."""
    t = _T_keys()
    js_keys = _all_js_T_keys()
    missing = js_keys - t
    assert not missing, (
        f"Keys used in T('...') calls but missing from template _T dict:\n"
        f"  {sorted(missing)}\n"
        f"Add them to templates/index.html in var _T = {{ ... }}"
    )


def test_no_dead_keys_in_T():
    """Every key in _T should be used by at least one T('key') call or be a nav_*."""
    t = _T_keys()
    used = _all_js_T_keys()
    # Also include keys used in Jinja2 {{ T('key') }} blocks
    html = TEMPLATE.read_text(encoding="utf-8")
    jinja_used = set(re.findall(r"\{\{.*?T\('([^']+)'\).*?\}\}", html))
    used.update(jinja_used)
    # nav_* keys are also used in rebuildTabs() as _tabName(t) = T('nav_'+t)
    nav = {k for k in _all_lang_keys() if k.startswith("nav_")}
    used.update(nav)
    dead = t - used
    assert not dead, (
        f"Keys in _T that are never used by any T('...') call:\n"
        f"  {sorted(dead)}"
    )


def test_T_keys_exist_in_lang():
    """Every key used in T('...') must exist in both lang files."""
    lang = _all_lang_keys()
    js_keys = _all_js_T_keys()
    missing = js_keys - lang
    assert not missing, (
        f"Keys used in T('...') but missing from lang/*.json:\n"
        f"  {sorted(missing)}"
    )


def test_all_nav_keys_in_T():
    """Every nav_* key from lang files must be in the JS _T dictionary."""
    t = _T_keys()
    nav = {k for k in _all_lang_keys() if k.startswith("nav_")}
    missing = nav - t
    assert not missing, (
        f"nav_* keys missing from template _T dict:\n"
        f"  {sorted(missing)}"
    )


def test_specific_nav_tests():
    """nav_tests must be in _T (regression)."""
    assert "nav_tests" in _T_keys(), "nav_tests missing from _T"
