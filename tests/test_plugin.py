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


def test_all_plugin_ids_include_core_and_extended():
    from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS, CORE_PLUGIN_IDS, EXTENDED_PLUGIN_IDS

    assert all(p in ALL_PLUGIN_IDS for p in CORE_PLUGIN_IDS)
    assert all(p in ALL_PLUGIN_IDS for p in EXTENDED_PLUGIN_IDS)
    assert "camera" in ALL_PLUGIN_IDS


def test_apply_dev_server_sets_url(tmp_path: Path):
    conf_path = tmp_path / "capacitor.config.json"
    conf_path.write_text("{}", encoding="utf-8")
    plugin = CapacitorPlugin(backend_url="http://192.168.1.56:8001")
    plugin.apply_dev_server(tmp_path, frontend_url="http://192.168.1.56:3000")
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    assert conf["server"]["url"] == "http://192.168.1.56:3000"
    assert conf["server"]["cleartext"] is True
    assert conf["server"]["androidScheme"] == "http"


def test_clear_dev_server_removes_url(tmp_path: Path):
    conf_path = tmp_path / "capacitor.config.json"
    conf_path.write_text(
        '{"server": {"url": "http://192.168.1.56:3000", "cleartext": true}}',
        encoding="utf-8",
    )
    plugin = CapacitorPlugin(backend_url="http://192.168.1.56:8001")
    plugin.clear_dev_server(tmp_path)
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    assert "url" not in conf.get("server", {})
    assert conf["server"]["androidScheme"] == "http"


def test_guess_lan_ip_returns_string():
    from reflex_capacitor.dev_util import guess_lan_ip

    ip = guess_lan_ip()
    assert isinstance(ip, str)
    assert ip.count(".") == 3


def test_scaffold_package_json_lists_all_plugins(tmp_path: Path, monkeypatch):
    from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS

    monkeypatch.chdir(tmp_path)
    plugin = CapacitorPlugin(plugins=ALL_PLUGIN_IDS)
    cap_root = tmp_path / "capacitor"
    plugin._scaffold(cap_root)
    plugin._configure(cap_root)
    pkg = json.loads((cap_root / "package.json").read_text(encoding="utf-8"))
    deps = pkg.get("dependencies", {})
    assert "@capacitor/core" in deps
    assert "@capacitor/camera" in deps
    assert "@capacitor/geolocation" in deps


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
