"""Idempotent Info.plist patches for Capacitor iOS projects."""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Final

from reflex_capacitor.bridge.plugins import PluginId

# Default App Store–safe usage strings (override via future CapacitorPlugin options).
_IOS_CAMERA_USAGE: Final = "Uses the camera to capture photos in the app."
_IOS_PHOTOS_USAGE: Final = "Uses your photo library to pick images."
_IOS_PHOTOS_ADD_USAGE: Final = "Saves photos you capture to your library when you choose."
_IOS_LOCATION_WHEN_IN_USE: Final = "Uses your location while you use map and location features."
_IOS_BLUETOOTH_ALWAYS: Final = "Uses Bluetooth to connect to nearby devices."

__all__ = [
    "apply_ios_plugin_permissions",
    "ensure_ios_background_mode",
    "ensure_ios_plist_string",
    "find_ios_info_plist",
]


def find_ios_info_plist(project_root: Path | str) -> Path | None:
    """Return ``ios/App/App/Info.plist`` when the iOS platform folder exists."""
    root = Path(project_root)
    candidates = (
        root / "ios" / "App" / "App" / "Info.plist",
        root / "ios" / "App" / "Info.plist",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _load_plist(path: Path) -> dict:
    with path.open("rb") as fh:
        data = plistlib.load(fh)
    if not isinstance(data, dict):
        msg = f"reflex-capacitor: unexpected Info.plist root in {path}"
        raise TypeError(msg)
    return data


def _save_plist(path: Path, data: dict) -> None:
    with path.open("wb") as fh:
        plistlib.dump(data, fh)


def ensure_ios_plist_string(path: Path | str, key: str, value: str) -> bool:
    """Set a string key in Info.plist when missing. Returns True if modified."""
    plist_path = Path(path)
    if not plist_path.is_file():
        return False
    data = _load_plist(plist_path)
    if key in data and data[key]:
        return False
    data[key] = value
    _save_plist(plist_path, data)
    return True


def ensure_ios_background_mode(path: Path | str, mode: str) -> bool:
    """Append a ``UIBackgroundModes`` entry when missing."""
    plist_path = Path(path)
    if not plist_path.is_file():
        return False
    data = _load_plist(plist_path)
    modes = data.get("UIBackgroundModes")
    if not isinstance(modes, list):
        modes = []
    if mode in modes:
        return False
    modes.append(mode)
    data["UIBackgroundModes"] = modes
    _save_plist(plist_path, data)
    return True


def apply_ios_plugin_permissions(
    project_root: Path | str,
    plugin_ids: tuple[PluginId, ...],
) -> list[str]:
    """Patch Info.plist usage descriptions for enabled plugins.

    Returns:
        Human-readable list of keys that were added (empty if nothing changed).
    """
    plist_path = find_ios_info_plist(project_root)
    if plist_path is None:
        return []

    added: list[str] = []
    if "camera" in plugin_ids:
        for key, text in (
            ("NSCameraUsageDescription", _IOS_CAMERA_USAGE),
            ("NSPhotoLibraryUsageDescription", _IOS_PHOTOS_USAGE),
            ("NSPhotoLibraryAddUsageDescription", _IOS_PHOTOS_ADD_USAGE),
        ):
            if ensure_ios_plist_string(plist_path, key, text):
                added.append(key)
    if "geolocation" in plugin_ids:
        if ensure_ios_plist_string(plist_path, "NSLocationWhenInUseUsageDescription", _IOS_LOCATION_WHEN_IN_USE):
            added.append("NSLocationWhenInUseUsageDescription")
    if "push-notifications" in plugin_ids:
        if ensure_ios_background_mode(plist_path, "remote-notification"):
            added.append("UIBackgroundModes:remote-notification")

    return added
