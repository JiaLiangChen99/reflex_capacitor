"""L1 integration tests — offline scaffold / bridge / manifest (no adb, no npm install).

Run with::

    pytest tests/test_integration_scaffold.py -q
    pytest tests/ -q -m integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reflex_capacitor.bridge.inject import _BRIDGE_BEGIN, _BRIDGE_END
from reflex_capacitor.bridge.plugins import (
    ALL_PLUGIN_IDS,
    CAPACITOR_PLUGIN_PACKAGES,
    CORE_PLUGIN_IDS,
    PHASE5_PLUGIN_IDS,
    vendor_script_filename,
)
from reflex_capacitor.plugin import CapacitorPlugin

from helpers import seed_android_manifest, seed_fake_node_modules, seed_static_export

pytestmark = pytest.mark.integration


def _make_plugin(
    *,
    plugins: tuple[str, ...] = CORE_PLUGIN_IDS,
    app_id: str = "com.example.integration",
    app_name: str = "Integration Test",
) -> CapacitorPlugin:
    return CapacitorPlugin(
        backend_url="https://api.example.com",
        app_id=app_id,
        app_name=app_name,
        plugins=plugins,
    )


def test_scaffold_writes_marker_gitignore_and_config(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    cap_root = app_root / "capacitor"
    plugin = _make_plugin(plugins=ALL_PLUGIN_IDS)

    plugin._scaffold(cap_root)
    plugin._configure(cap_root)

    assert (cap_root / ".reflex-capacitor").is_file()
    assert (cap_root / ".gitignore").is_file()
    assert "node_modules/" in (cap_root / ".gitignore").read_text(encoding="utf-8")

    conf = json.loads((cap_root / "capacitor.config.json").read_text(encoding="utf-8"))
    assert conf["appId"] == "com.example.integration"
    assert conf["appName"] == "Integration Test"
    assert conf["webDir"] == "www"
    assert conf["server"]["cleartext"] is False
    assert conf["server"]["androidScheme"] == "https"


def test_scaffold_package_json_lists_requested_plugins(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    cap_root = app_root / "capacitor"
    plugins = ALL_PLUGIN_IDS + PHASE5_PLUGIN_IDS
    plugin = _make_plugin(plugins=plugins)

    plugin._scaffold(cap_root)
    plugin._configure(cap_root)

    deps = json.loads((cap_root / "package.json").read_text(encoding="utf-8"))["dependencies"]
    assert deps["@capacitor/core"].startswith("^")
    assert "@capacitor/push-notifications" in deps
    assert "@capacitor/camera" in deps
    for plugin_id in plugins:
        assert CAPACITOR_PLUGIN_PACKAGES[plugin_id] in deps


def test_post_build_copies_export_and_injects_bridge(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    static_dir = app_root / ".web" / "build" / "client"
    seed_static_export(static_dir)

    plugin = _make_plugin(plugins=("toast", "app"))
    plugin.post_build(static_dir=static_dir)

    cap_root = app_root / "capacitor"
    www = cap_root / "www"
    assert (cap_root / ".reflex-capacitor").is_file()
    assert (www / "index.html").is_file()
    assert (www / "assets" / "app.js").is_file()
    assert (www / "assets" / "reflex-capacitor" / "bridge.js").is_file()

    html = (www / "index.html").read_text(encoding="utf-8")
    assert html.count(_BRIDGE_BEGIN) == 1
    assert "toast.plugin.js" in html
    assert "app.plugin.js" in html
    assert _BRIDGE_END in html


def test_post_build_is_idempotent_when_scaffold_exists(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    static_dir = app_root / "export"
    seed_static_export(static_dir)
    plugin = _make_plugin(plugins=("clipboard",))

    plugin.post_build(static_dir=static_dir)
    first_marker = (app_root / "capacitor" / ".reflex-capacitor").read_text(encoding="utf-8")

    (static_dir / "index.html").write_text(
        "<!doctype html><html><body><p>v2</p></body></html>\n",
        encoding="utf-8",
    )
    plugin.post_build(static_dir=static_dir)

    cap_root = app_root / "capacitor"
    assert (cap_root / ".reflex-capacitor").read_text(encoding="utf-8") == first_marker
    assert "v2" in (cap_root / "www" / "index.html").read_text(encoding="utf-8")


def test_finalize_bridge_copies_vendor_scripts(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    cap_root = app_root / "capacitor"
    www = cap_root / "www"
    www.mkdir(parents=True)
    (www / "index.html").write_text("<html><body></body></html>\n", encoding="utf-8")

    plugins = ("toast", "clipboard")
    seed_fake_node_modules(cap_root, plugins)
    plugin = _make_plugin(plugins=plugins)
    plugin.finalize_bridge(cap_root)

    vendor = www / "assets" / "reflex-capacitor" / "vendor"
    assert (vendor / "capacitor.js").is_file()
    for plugin_id in plugins:
        assert (vendor / vendor_script_filename(plugin_id)).is_file()


def test_finalize_bridge_patches_android_permissions(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    cap_root = app_root / "capacitor"
    www = cap_root / "www"
    www.mkdir(parents=True)
    (www / "index.html").write_text("<html><body></body></html>\n", encoding="utf-8")

    plugins = ALL_PLUGIN_IDS + PHASE5_PLUGIN_IDS
    seed_fake_node_modules(cap_root, plugins)
    manifest = seed_android_manifest(cap_root)

    plugin = _make_plugin(plugins=plugins)
    plugin.finalize_bridge(cap_root)

    text = manifest.read_text(encoding="utf-8")
    assert "android.permission.POST_NOTIFICATIONS" in text
    assert "android.permission.VIBRATE" in text
    assert "android.permission.CAMERA" in text
    assert "android.permission.ACCESS_FINE_LOCATION" in text
    assert text.count("android.permission.POST_NOTIFICATIONS") == 1


def test_finalize_bridge_patches_ios_plist_when_present(app_root: Path, monkeypatch):
    monkeypatch.chdir(app_root)
    cap_root = app_root / "capacitor"
    www = cap_root / "www"
    www.mkdir(parents=True)
    (www / "index.html").write_text("<html><body></body></html>\n", encoding="utf-8")

    import plistlib

    plist = cap_root / "ios" / "App" / "App" / "Info.plist"
    plist.parent.mkdir(parents=True)
    with plist.open("wb") as fh:
        plistlib.dump({}, fh)

    plugins = ("camera", "geolocation")
    seed_fake_node_modules(cap_root, plugins)
    seed_android_manifest(cap_root)

    plugin = _make_plugin(plugins=plugins)
    plugin.finalize_bridge(cap_root)

    with plist.open("rb") as fh:
        data = plistlib.load(fh)
    assert data.get("NSCameraUsageDescription")
    assert data.get("NSLocationWhenInUseUsageDescription")


def test_l1_pipeline_scaffold_post_build_finalize(app_root: Path, monkeypatch):
    """End-to-end offline flow matching ``sync`` without npm install or cap sync."""
    monkeypatch.chdir(app_root)
    static_dir = app_root / "export"
    seed_static_export(static_dir)

    plugins = CORE_PLUGIN_IDS + ("camera",) + PHASE5_PLUGIN_IDS
    plugin = _make_plugin(plugins=plugins, app_id="dev.reflex.l1.test")

    plugin.post_build(static_dir=static_dir)
    cap_root = app_root / "capacitor"
    seed_fake_node_modules(cap_root, plugins)
    seed_android_manifest(cap_root)
    plugin.finalize_bridge(cap_root)

    pkg = json.loads((cap_root / "package.json").read_text(encoding="utf-8"))
    assert "@capacitor/push-notifications" in pkg["dependencies"]

    html = (cap_root / "www" / "index.html").read_text(encoding="utf-8")
    assert _BRIDGE_BEGIN in html
    assert "camera.plugin.js" in html

    vendor = cap_root / "www" / "assets" / "reflex-capacitor" / "vendor"
    assert (vendor / "push-notifications.plugin.js").is_file()

    manifest = (cap_root / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    assert "POST_NOTIFICATIONS" in manifest
