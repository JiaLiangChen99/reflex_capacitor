"""Tests for iOS Info.plist permission patching."""

from __future__ import annotations

import plistlib
from pathlib import Path

from reflex_capacitor.bridge.ios_plist import (
    apply_ios_plugin_permissions,
    ensure_ios_background_mode,
    ensure_ios_plist_string,
    find_ios_info_plist,
)
from reflex_capacitor.bridge.plugins import CORE_PLUGIN_IDS


def _write_plist(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh)


def test_find_ios_info_plist_standard_layout(tmp_path: Path):
    plist = tmp_path / "ios" / "App" / "App" / "Info.plist"
    _write_plist(plist, {"CFBundleIdentifier": "com.example.app"})
    assert find_ios_info_plist(tmp_path) == plist


def test_ensure_ios_plist_string_idempotent(tmp_path: Path):
    plist = tmp_path / "Info.plist"
    _write_plist(plist, {})
    assert ensure_ios_plist_string(plist, "NSCameraUsageDescription", "Camera reason") is True
    assert ensure_ios_plist_string(plist, "NSCameraUsageDescription", "Other") is False
    with plist.open("rb") as fh:
        data = plistlib.load(fh)
    assert data["NSCameraUsageDescription"] == "Camera reason"


def test_apply_ios_plugin_permissions_camera_and_geo(tmp_path: Path):
    plist = tmp_path / "ios" / "App" / "App" / "Info.plist"
    _write_plist(plist, {})
    added = apply_ios_plugin_permissions(tmp_path, CORE_PLUGIN_IDS + ("camera", "geolocation"))
    assert "NSCameraUsageDescription" in added
    assert "NSLocationWhenInUseUsageDescription" in added
    with plist.open("rb") as fh:
        data = plistlib.load(fh)
    assert data["NSCameraUsageDescription"]
    assert data["NSLocationWhenInUseUsageDescription"]


def test_ensure_ios_background_mode_idempotent(tmp_path: Path):
    plist = tmp_path / "ios" / "App" / "App" / "Info.plist"
    _write_plist(plist, {})
    assert ensure_ios_background_mode(plist, "remote-notification") is True
    assert ensure_ios_background_mode(plist, "remote-notification") is False


def test_apply_ios_push_background_mode(tmp_path: Path):
    plist = tmp_path / "ios" / "App" / "App" / "Info.plist"
    _write_plist(plist, {})
    added = apply_ios_plugin_permissions(tmp_path, ("push-notifications",))
    assert "UIBackgroundModes:remote-notification" in added


def test_apply_ios_skips_when_no_ios_folder(tmp_path: Path):
    assert apply_ios_plugin_permissions(tmp_path, CORE_PLUGIN_IDS) == []
