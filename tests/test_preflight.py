"""Unit tests for host dependency preflight helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from reflex_capacitor import preflight


def test_format_missing_report_lists_names() -> None:
    missing = [
        preflight.Check(
            name="Node.js",
            ok=False,
            detail="not found",
            remediation="Install Node",
        ),
        preflight.Check(
            name="JDK 17+",
            ok=False,
            detail="too old",
            remediation="Install JDK",
        ),
    ]
    text = preflight.format_missing_report(missing)
    assert "Node.js" in text
    assert "JDK 17+" in text
    assert "does not install" in text
    assert "reflex-capacitor doctor" in text


def test_failed_required_filters() -> None:
    checks = [
        preflight.Check(name="a", ok=False, detail="x", required=True),
        preflight.Check(name="b", ok=False, detail="y", required=False),
        preflight.Check(name="c", ok=True, detail="z", required=True),
    ]
    assert [c.name for c in preflight.failed_required(checks)] == ["a"]
    assert [c.name for c in preflight.failed_optional(checks)] == ["b"]


def test_sdk_helpers(tmp_path: Path) -> None:
    assert not preflight._sdk_has_platforms(tmp_path)
    assert not preflight._sdk_has_build_tools(tmp_path)
    (tmp_path / "platforms" / "android-35").mkdir(parents=True)
    (tmp_path / "build-tools" / "35.0.0").mkdir(parents=True)
    (tmp_path / "platform-tools").mkdir()
    assert preflight._sdk_has_platforms(tmp_path)
    assert preflight._sdk_has_build_tools(tmp_path)
    assert preflight._sdk_has_platform_tools(tmp_path)


def test_run_checks_android_includes_jdk_and_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight, "_reflex_ok", lambda: (True, "reflex ok"))
    monkeypatch.setattr(preflight, "_version", lambda cmd: "v1" if cmd else None)
    monkeypatch.setattr(preflight, "_which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(preflight, "_android_sdk_root", lambda: None)
    monkeypatch.setattr(preflight, "_java_major", lambda: (False, "no java"))

    checks = preflight.run_checks(need_android=True)
    names = {c.name for c in checks}
    assert "Reflex" in names
    assert "Node.js" in names
    assert "Android SDK" in names
    assert "JDK 17+" in names
    missing = preflight.failed_required(checks)
    assert any(c.name == "Android SDK" for c in missing)
    assert any(c.name == "JDK 17+" for c in missing)


def test_adb_required_only_with_need_device(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sdk = tmp_path / "sdk"
    (sdk / "platform-tools").mkdir(parents=True)
    (sdk / "platforms" / "android-35").mkdir(parents=True)
    (sdk / "build-tools" / "35.0.0").mkdir(parents=True)

    monkeypatch.setattr(preflight, "_reflex_ok", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "_version", lambda cmd: None if cmd == ["adb"] else "v1")
    monkeypatch.setattr(preflight, "_which", lambda name: None if name == "adb" else f"/bin/{name}")
    monkeypatch.setattr(preflight, "_android_sdk_root", lambda: str(sdk))
    monkeypatch.setattr(preflight, "_java_major", lambda: (True, "21"))

    build_checks = preflight.run_checks(need_android=True, need_device=False)
    assert not any(c.name == "adb" and c.required for c in build_checks)
    assert preflight.failed_required(build_checks) == []

    run_checks = preflight.run_checks(need_android=True, need_device=True)
    adb = next(c for c in run_checks if c.name == "adb")
    assert adb.required and not adb.ok
    assert preflight.failed_required(run_checks)
