"""Helpers for L3 device smoke tests (adb required)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def adb_path() -> str | None:
    """Return ``adb`` executable path if available."""
    return shutil.which("adb")


def list_adb_devices() -> list[str]:
    """Return serial ids of connected ``adb devices`` in ``device`` state."""
    adb = adb_path()
    if not adb:
        return []
    try:
        result = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    devices: list[str] = []
    for line in (result.stdout or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def pick_adb_device() -> str | None:
    """Return the first connected device serial, if any."""
    devices = list_adb_devices()
    return devices[0] if devices else None


def project_root() -> Path:
    """Repository root (parent of ``tests/``)."""
    return Path(__file__).resolve().parent.parent


def capacitor_config_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "capacitor" / "capacitor.config.json"


def read_app_id(root: Path | None = None) -> str | None:
    """Read ``appId`` from ``capacitor/capacitor.config.json`` when present."""
    path = capacitor_config_path(root)
    if not path.is_file():
        return None
    try:
        conf = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    app_id = conf.get("appId")
    return str(app_id) if app_id else None


def debug_apk_path(root: Path | None = None) -> Path:
    """Default Gradle debug APK output path."""
    base = root or project_root()
    return (
        base
        / "capacitor"
        / "android"
        / "app"
        / "build"
        / "outputs"
        / "apk"
        / "debug"
        / "app-debug.apk"
    )


def smoke_script_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "scripts" / "device-smoke.sh"
