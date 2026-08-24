"""Unit tests for CapacitorPlugin (no Android SDK required)."""

from __future__ import annotations

import json
from pathlib import Path

from reflex_capacitor.config import DEV_BACKEND_URL_ENV
from reflex_capacitor.plugin import CapacitorPlugin


def test_update_env_json_https_uses_wss(monkeypatch):
    monkeypatch.setenv(DEV_BACKEND_URL_ENV, "https://api.example.com")
    env = CapacitorPlugin().update_env_json()
    assert env is not None
    assert env["PING"] == "https://api.example.com/ping"
    assert env["EVENT"] == "wss://api.example.com/_event"


def test_update_env_json_http_uses_ws(monkeypatch):
    monkeypatch.setenv(DEV_BACKEND_URL_ENV, "http://192.168.1.56:8001")
    env = CapacitorPlugin().update_env_json()
    assert env is not None
    assert env["EVENT"] == "ws://192.168.1.56:8001/_event"


def test_update_env_json_without_backend_is_noop():
    assert CapacitorPlugin(backend_url=None).update_env_json() is None


def test_apply_capacitor_config_http_cleartext(tmp_path: Path):
    conf_path = tmp_path / "capacitor.config.json"
    conf_path.write_text("{}", encoding="utf-8")
    CapacitorPlugin(backend_url="http://192.168.1.56:8001")._apply_capacitor_config(
        conf_path, "Shell", "dev.reflex.demo"
    )
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    assert conf["server"]["cleartext"] is True
    assert conf["server"]["androidScheme"] == "http"


def test_apply_capacitor_config_https_no_cleartext(tmp_path: Path):
    conf_path = tmp_path / "capacitor.config.json"
    conf_path.write_text('{"server": {"cleartext": true, "androidScheme": "http"}}', encoding="utf-8")
    CapacitorPlugin(backend_url="https://api.example.com")._apply_capacitor_config(
        conf_path, "Shell", "dev.reflex.demo"
    )
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    assert conf["server"]["cleartext"] is False
    assert conf["server"]["androidScheme"] == "https"


def test_demo_plugins_include_p1():
    from reflex_capacitor.bridge.plugins import DEFAULT_PLUGINS, DEMO_PLUGINS, P1_PLUGINS

    assert all(p in DEMO_PLUGINS for p in DEFAULT_PLUGINS)
    assert all(p in DEMO_PLUGINS for p in P1_PLUGINS)
    assert "camera" in DEMO_PLUGINS


def test_apply_icon_copies_to_android_mipmaps(tmp_path: Path, monkeypatch):
    icon_src = tmp_path / "assets" / "icon.png"
    icon_src.parent.mkdir(parents=True)
    icon_src.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    res = tmp_path / "capacitor" / "android" / "app" / "src" / "main" / "res" / "mipmap-mdpi"
    res.mkdir(parents=True)
    (res / "ic_launcher.png").write_bytes(b"old")

    monkeypatch.chdir(tmp_path)
    plugin = CapacitorPlugin(icon="assets/icon.png")
    plugin._apply_icon(tmp_path / "capacitor")

    assert (res / "ic_launcher.png").read_bytes().startswith(b"\x89PNG")
    assert (res / "ic_launcher_round.png").is_file()
