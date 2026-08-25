"""Preflight checks for host toolchains (Node / JDK / Android SDK / Xcode).

Policy: **detect and report only** — never download or install SDKs, JDKs, or
Node for the user. Project-local ``npm install`` in ``capacitor/`` is separate
(app dependencies, not host tooling).
"""

from __future__ import annotations

import dataclasses
import os
import re
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


def _run_text(cmd: list[str]) -> str | None:
    """Return combined stdout+stderr text, or None if the command cannot run."""
    resolved = _which(cmd[0])
    if not resolved:
        return None
    try:
        result = subprocess.run(
            [resolved, *cmd[1:]],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return ((result.stdout or "") + (result.stderr or "")).strip()


def _version(cmd: list[str]) -> str | None:
    """Return the first line of ``cmd --version``, or None if unavailable."""
    text = _run_text([*cmd, "--version"])
    if text is None:
        return None
    lines = text.splitlines()
    return lines[0] if lines else "installed (version unknown)"


def _android_sdk_root() -> str | None:
    """Return a plausible Android SDK root if one exists on disk."""
    candidates = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        str(Path.home() / "Android" / "Sdk"),
        str(Path.home() / "Library" / "Android" / "sdk"),
        str(Path.home() / "AppData" / "Local" / "Android" / "Sdk"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk"),
        r"C:\Android\Sdk",
        r"D:\Android\Sdk",
        "/usr/lib/android-sdk",
        "/opt/android-sdk",
    ]
    for raw in candidates:
        if not raw:
            continue
        root = Path(raw)
        if (root / "platform-tools").is_dir() or (root / "platforms").is_dir():
            return str(root)
    return None


def _sdk_has_platforms(sdk: Path) -> bool:
    platforms = sdk / "platforms"
    if not platforms.is_dir():
        return False
    return any(platforms.glob("android-*"))


def _sdk_has_build_tools(sdk: Path) -> bool:
    build_tools = sdk / "build-tools"
    if not build_tools.is_dir():
        return False
    return any(p.is_dir() for p in build_tools.iterdir())


def _sdk_has_platform_tools(sdk: Path) -> bool:
    return (sdk / "platform-tools").is_dir()


def _java_major() -> tuple[bool, str]:
    """Return (ok_for_android, detail). Android Gradle Plugin needs JDK 17+ (21 OK)."""
    java_home = os.environ.get("JAVA_HOME", "").strip()
    java_bin: str | None = None
    if java_home:
        candidate = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if candidate.is_file():
            java_bin = str(candidate)
    if not java_bin:
        java_bin = _which("java")
    if not java_bin:
        return False, "not found (set JAVA_HOME or add JDK 17+ to PATH)"

    try:
        result = subprocess.run(
            [java_bin, "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False, f"cannot execute {java_bin}"
    text = ((result.stderr or "") + (result.stdout or "")).strip()
    first = text.splitlines()[0] if text else java_bin
    match = re.search(r'version\s+"?(?P<ver>[\d._]+)', text)
    if not match:
        return False, f"{first} (could not parse version; need JDK 17+)"
    ver = match.group("ver")
    major_s = ver.split(".", 1)[0]
    if major_s == "1" and "." in ver:
        major_s = ver.split(".")[1]
    try:
        major = int(major_s)
    except ValueError:
        return False, f"{first} (unparsed version {ver!r}; need JDK 17+)"
    if major < 17:
        return False, f"{first} — need JDK 17+ (found major {major})"
    where = f"JAVA_HOME={java_home}" if java_home else java_bin
    return True, f"{first} ({where})"


def _reflex_ok() -> tuple[bool, str]:
    """Check the Reflex CLI is importable / on PATH."""
    sibling = Path(sys.executable).parent / ("reflex.exe" if os.name == "nt" else "reflex")
    if sibling.is_file():
        ver = _run_text([str(sibling), "--version"])
        line = (ver or "").splitlines()[0] if ver else "present"
        return True, f"{sibling} — {line}"
    which = _which("reflex")
    if which:
        ver = _run_text([which, "--version"])
        line = (ver or "").splitlines()[0] if ver else which
        return True, line
    try:
        result = subprocess.run(
            [sys.executable, "-m", "reflex", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            out = ((result.stdout or "") + (result.stderr or "")).strip()
            return True, out.splitlines()[0] if out else "python -m reflex"
    except OSError:
        pass
    return False, "not found — pip install 'reflex>=0.9' in this environment"


def format_missing_report(missing: list[Check], *, heading: str | None = None) -> str:
    """Build a multi-line error listing every failed required check."""
    title = heading or (
        "missing required host dependencies — install them yourself, then re-run "
        "(this CLI does not install Node / JDK / Android SDK / Xcode):\n"
    )
    lines = [title]
    for check in missing:
        lines.append(f"  ✗ {check.name}: {check.detail}")
        if check.remediation:
            lines.extend(f"      {line}" for line in check.remediation.splitlines())
        lines.append("")
    lines.append("Full report:  reflex-capacitor doctor --android   # or --ios")
    lines.append("Recheck only: reflex-capacitor check --android")
    return "\n".join(lines)


def run_checks(
    *,
    need_android: bool = False,
    need_ios: bool = False,
    need_device: bool = False,
) -> list[Check]:
    """Run toolchain checks needed to sync / build / run a Capacitor shell.

    Args:
        need_android: Require Android SDK pieces + JDK 17+ (for init/build/run).
        need_ios: Require Xcode tooling when meaningful.
        need_device: Also require ``adb`` (for ``run`` / ``dev`` on device).

    Returns:
        Ordered check results. Failed *required* items should abort the CLI.
    """
    checks: list[Check] = []

    reflex_ok, reflex_detail = _reflex_ok()
    checks.append(
        Check(
            name="Reflex",
            ok=reflex_ok,
            detail=reflex_detail,
            remediation=(
                "Install Reflex in the same Python env as reflex-capacitor:\n"
                "  pip install 'reflex>=0.9'"
            ),
        )
    )

    node = _version(["node"])
    checks.append(
        Check(
            name="Node.js",
            ok=node is not None,
            detail=node or "not found on PATH",
            remediation=(
                "Install Node.js 20+ from https://nodejs.org/ then restart the shell.\n"
                "  (Windows: winget install OpenJS.NodeJS.LTS)\n"
                "This tool will not install Node for you."
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
        sdk_raw = _android_sdk_root()
        sdk_ok = sdk_raw is not None
        checks.append(
            Check(
                name="Android SDK",
                ok=sdk_ok,
                detail=sdk_raw or "not found (set ANDROID_HOME)",
                remediation=(
                    "Install Android Studio (or command-line SDK), then set:\n"
                    "  export ANDROID_HOME=/path/to/Android/Sdk\n"
                    "  export PATH=\"$ANDROID_HOME/platform-tools:$PATH\"\n"
                    "Windows: ANDROID_HOME=%LOCALAPPDATA%\\Android\\Sdk\n"
                    "Docs: https://developer.android.com/studio\n"
                    "This tool will not download the SDK for you."
                ),
                required=True,
            )
        )

        java_ok, java_detail = _java_major()
        checks.append(
            Check(
                name="JDK 17+",
                ok=java_ok,
                detail=java_detail,
                remediation=(
                    "Install Temurin / OpenJDK 17 or 21 and set JAVA_HOME, e.g.:\n"
                    "  export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64\n"
                    "  export PATH=\"$JAVA_HOME/bin:$PATH\"\n"
                    "Android Gradle Plugin will fail without JDK 17+."
                ),
                required=True,
            )
        )

        if sdk_raw:
            sdk = Path(sdk_raw)
            has_pt = _sdk_has_platform_tools(sdk)
            checks.append(
                Check(
                    name="Android platform-tools",
                    ok=has_pt,
                    detail=str(sdk / "platform-tools") if has_pt else "missing under SDK",
                    remediation=(
                        "In Android Studio SDK Manager install 'Android SDK Platform-Tools',\n"
                        "or: sdkmanager 'platform-tools'"
                    ),
                    required=True,
                )
            )
            has_plat = _sdk_has_platforms(sdk)
            plat_detail = "ok" if has_plat else "no platforms/android-* under SDK"
            if has_plat:
                names = sorted(p.name for p in (sdk / "platforms").glob("android-*"))
                plat_detail = ", ".join(names)
            checks.append(
                Check(
                    name="Android platforms",
                    ok=has_plat,
                    detail=plat_detail,
                    remediation=(
                        "Install at least one Android platform (e.g. Android 35):\n"
                        "  sdkmanager 'platforms;android-35'"
                    ),
                    required=True,
                )
            )
            has_bt = _sdk_has_build_tools(sdk)
            bt_detail = "ok" if has_bt else "no build-tools/* under SDK"
            if has_bt:
                names = sorted(p.name for p in (sdk / "build-tools").iterdir() if p.is_dir())
                bt_detail = ", ".join(names)
            checks.append(
                Check(
                    name="Android build-tools",
                    ok=has_bt,
                    detail=bt_detail,
                    remediation=(
                        "Install build-tools, e.g.:\n"
                        "  sdkmanager 'build-tools;35.0.0'"
                    ),
                    required=True,
                )
            )

        adb = _version(["adb"])
        checks.append(
            Check(
                name="adb",
                ok=adb is not None,
                detail=adb or "not found on PATH",
                remediation=(
                    "Add platform-tools to PATH:\n"
                    "  export PATH=\"$ANDROID_HOME/platform-tools:$PATH\""
                ),
                required=need_device,
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
                    "  xcode-select --install\n"
                    "This tool will not install Xcode for you."
                    if on_macos
                    else "Use a Mac for iOS, or build Android on this machine."
                ),
                required=True,
            )
        )

    return checks


def failed_required(checks: list[Check]) -> list[Check]:
    """Return required checks that failed."""
    return [c for c in checks if c.required and not c.ok]


def failed_optional(checks: list[Check]) -> list[Check]:
    """Return optional checks that failed (warnings)."""
    return [c for c in checks if not c.required and not c.ok]
