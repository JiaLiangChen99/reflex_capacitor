"""Preflight checks for Node / Capacitor tooling."""

from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import sys
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class Check:
    """Result of a single preflight check."""

    name: str
    ok: bool
    detail: str
    remediation: str = ""
    required: bool = True


def _which(name: str) -> str | None:
    """Resolve an executable, preferring ``.cmd`` shims on Windows."""
    found = shutil.which(name)
    if found:
        return found
    if sys.platform == "win32":
        return shutil.which(f"{name}.cmd")
    return None


def _version(cmd: list[str]) -> str | None:
    """Return the first line of ``cmd --version``, or None if unavailable."""
    resolved = _which(cmd[0])
    if not resolved:
        return None
    argv = [resolved, *cmd[1:], "--version"]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    out = (result.stdout or result.stderr or "").strip().splitlines()
    return out[0] if out else "installed (version unknown)"


def _android_sdk_root() -> str | None:
    """Return a plausible Android SDK root if one exists on disk."""
    candidates = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        str(Path.home() / "AppData" / "Local" / "Android" / "Sdk"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk"),
        r"C:\Android\Sdk",
        r"D:\Android\Sdk",
    ]
    for raw in candidates:
        if not raw:
            continue
        root = Path(raw)
        # native-run looks for platform-tools under the SDK root.
        if (root / "platform-tools").is_dir() or (root / "platforms").is_dir():
            return str(root)
    return None


def run_checks(*, need_android: bool = False, need_ios: bool = False) -> list[Check]:
    """Run toolchain checks needed to sync / run a Capacitor shell.

    Args:
        need_android: Also require Android SDK when True (for ``run android``).
        need_ios: Also require Xcode tooling when True (macOS only meaningful).

    Returns:
        Ordered check results.
    """
    checks: list[Check] = []

    node = _version(["node"])
    checks.append(
        Check(
            name="Node.js",
            ok=node is not None,
            detail=node or "not found on PATH",
            remediation=(
                "Install Node.js 20+ from https://nodejs.org/ then restart the shell.\n"
                "  (or: winget install OpenJS.NodeJS.LTS)"
            ),
        )
    )

    npm = _version(["npm"])
    checks.append(
        Check(
            name="npm",
            ok=npm is not None,
            detail=npm or "not found on PATH",
            remediation="npm ships with Node.js — reinstall Node from https://nodejs.org/",
        )
    )

    npx = _which("npx") is not None
    checks.append(
        Check(
            name="npx",
            ok=npx,
            detail="available" if npx else "not found on PATH",
            remediation="npx ships with npm/Node.js — reinstall Node from https://nodejs.org/",
        )
    )

    if need_android:
        sdk = _android_sdk_root()
        checks.append(
            Check(
                name="Android SDK",
                ok=sdk is not None,
                detail=sdk or "not found (ANDROID_HOME / default Local\\Android\\Sdk)",
                remediation=(
                    "Install Android Studio, then open it once to finish the SDK setup wizard:\n"
                    "  https://developer.android.com/studio\n"
                    "After install, set a User env var and restart the terminal:\n"
                    "  ANDROID_HOME=%LOCALAPPDATA%\\Android\\Sdk\n"
                    "  Path += %ANDROID_HOME%\\platform-tools\n"
                    "Or open the project in Android Studio (no CLI SDK needed to start):\n"
                    "  reflex-capacitor open android"
                ),
                required=True,
            )
        )
        adb = _version(["adb"])
        java = _version(["java"])
        checks.append(
            Check(
                name="Android adb",
                ok=adb is not None,
                detail=adb or "not found on PATH (platform-tools)",
                remediation=(
                    "Add SDK platform-tools to PATH:\n"
                    "  %LOCALAPPDATA%\\Android\\Sdk\\platform-tools"
                ),
                required=False,
            )
        )
        checks.append(
            Check(
                name="Java",
                ok=java is not None,
                detail=java or "not found on PATH",
                remediation="Install a JDK 17+ (Android Studio bundles one) and add it to PATH.",
                required=False,
            )
        )

    if need_ios:
        on_macos = sys.platform == "darwin"
        xcode = _version(["xcodebuild"]) if on_macos else None
        checks.append(
            Check(
                name="Xcode",
                ok=bool(xcode) if on_macos else False,
                detail=(
                    xcode
                    if on_macos and xcode
                    else (
                        "iOS builds require macOS + Xcode"
                        if not on_macos
                        else "xcodebuild not found"
                    )
                ),
                remediation=(
                    "Install Xcode from the App Store, then:\n"
                    "  xcode-select --install"
                    if on_macos
                    else "Use a Mac to build/run the iOS target, or develop Android on this machine."
                ),
                required=False,
            )
        )

    return checks


def failed_required(checks: list[Check]) -> list[Check]:
    """Return required checks that failed."""
    return [c for c in checks if c.required and not c.ok]
