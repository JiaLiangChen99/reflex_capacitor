"""Unit tests for bridge HTML injection (no Capacitor/npm required)."""

from __future__ import annotations

from pathlib import Path

from reflex_capacitor.bridge.inject import (
    _BRIDGE_BEGIN,
    _BRIDGE_END,
    build_bridge_snippet,
    inject_index_html,
    install_bridge,
)
from reflex_capacitor.bridge.plugins import DEFAULT_PLUGINS


def test_build_bridge_snippet_includes_marker_and_bridge_js():
    snippet = build_bridge_snippet(("toast", "clipboard"))
    assert _BRIDGE_BEGIN in snippet
    assert _BRIDGE_END in snippet
    assert "capacitor.js" in snippet
    assert "toast.plugin.js" in snippet
    assert "clipboard.plugin.js" in snippet
    assert "assets/reflex-capacitor/bridge.js" in snippet


def test_inject_index_html_idempotent(tmp_path: Path):
    www = tmp_path / "www"
    www.mkdir()
    index = www / "index.html"
    index.write_text("<!doctype html><html><body><p>app</p></body></html>\n", encoding="utf-8")
    plugins = ("toast",)

    inject_index_html(www, plugins)
    first = index.read_text(encoding="utf-8")
    assert first.count(_BRIDGE_BEGIN) == 1
    assert "toast.plugin.js" in first

    inject_index_html(www, DEFAULT_PLUGINS[:3])
    second = index.read_text(encoding="utf-8")
    assert second.count(_BRIDGE_BEGIN) == 1
    assert "local-notifications.plugin.js" in second


def test_install_bridge_copies_js_and_injects(tmp_path: Path):
    www = tmp_path / "www"
    www.mkdir()
    (www / "index.html").write_text("<html><body></body></html>\n", encoding="utf-8")

    install_bridge(www, ("app",))

    assert (www / "assets" / "reflex-capacitor" / "bridge.js").is_file()
    assert (www / "assets" / "reflex-capacitor" / "image-editor.js").is_file()
    html = (www / "index.html").read_text(encoding="utf-8")
    assert _BRIDGE_BEGIN in html
    assert "image-editor.js" in html
    assert "app.plugin.js" in html
