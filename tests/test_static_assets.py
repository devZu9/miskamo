"""Verify all static assets serve 200, not 404."""
import re


def _extract_static_links(html):
    paths = set()
    for pattern in (r'src="(/static/[^"]+)"', r'href="(/static/[^"]+)"'):
        for m in re.finditer(pattern, html):
            paths.add(m.group(1))
    return sorted(paths)


def test_main_page_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_favicon_served(client):
    r = client.get("/static/core/favicon.svg")
    assert r.status_code == 200


def test_each_module_js_served(client):
    modules = [
        ("midigen", "tab-midigen.js"),
        ("audio2midi", "tab-audio2midi.js"),
        ("dataset", "tab-dataset.js"),
        ("history", "tab-history.js"),
        ("testing", "tab-tests.js"),
        ("train", "tab-train.js"),
    ]
    for mod_dir, js_file in modules:
        r = client.get(f"/modules/{mod_dir}/static/{js_file}")
        assert r.status_code == 200, f"Module JS missing: {mod_dir}/{js_file}"


def test_settings_js_served(client):
    r = client.get("/static/core/tab-settings.js")
    assert r.status_code == 200
