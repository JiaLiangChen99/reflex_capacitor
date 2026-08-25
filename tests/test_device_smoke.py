"""L3 device smoke tests — require adb + connected Android device.

Skipped automatically when no device is attached (CI-safe).

Run::

    pytest tests/test_device_smoke.py -q -m device
    ./scripts/device-smoke.sh
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from device_util import (
    debug_apk_path,
    pick_adb_device,
    project_root,
    read_app_id,
    smoke_script_path,
)

pytestmark = pytest.mark.device


@pytest.fixture(scope="module")
def adb_serial() -> str:
    """First connected adb device serial."""
    serial = pick_adb_device()
    if not serial:
        pytest.skip("no adb device — connect phone with USB debugging or start emulator")
    return serial


@pytest.fixture(scope="module")
def root() -> Path:
    return project_root()


def test_capacitor_config_has_app_id(root: Path) -> None:
    app_id = read_app_id(root)
    if not app_id:
        pytest.skip("capacitor/capacitor.config.json missing — run reflex-capacitor init/sync first")
    assert "." in app_id


def test_adb_lists_device(adb_serial: str) -> None:
    assert adb_serial


def test_device_smoke_script(root: Path, adb_serial: str) -> None:
    """Run ``scripts/device-smoke.sh`` (expects prebuilt APK unless SKIP_BUILD=0)."""
    script = smoke_script_path(root)
    if not script.is_file():
        pytest.fail(f"missing smoke script at {script}")

    apk = debug_apk_path(root)
    env = os.environ.copy()
    env["ADB_SERIAL"] = adb_serial
    env.setdefault("SKIP_BUILD", "1" if apk.is_file() else "0")
    env.setdefault("SKIP_DEEP_LINK", "1")  # intent-filter often not configured in dev trees

    if env["SKIP_BUILD"] == "1" and not apk.is_file():
        pytest.skip(
            f"debug APK missing at {apk} — run: "
            "reflex-capacitor sync && cd capacitor/android && ./gradlew assembleDebug"
        )

    result = subprocess.run(
        ["bash", str(script)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=900 if env.get("SKIP_BUILD") == "0" else 120,
        check=False,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        pytest.fail(
            f"device-smoke.sh exited {result.returncode}\n"
            f"--- stdout/stderr ---\n{combined[-4000:]}"
        )
    assert "[reflex-capacitor]" in combined or "bridge logcat OK" in combined
