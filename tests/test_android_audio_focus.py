"""Tests for Android AudioFocus plugin install (TTS duck/pause music)."""

from __future__ import annotations

from pathlib import Path

from reflex_capacitor.bridge.android_audio_focus import (
    find_main_activity,
    install_audio_focus_plugin,
)


def _scaffold_android(tmp: Path, *, java: bool = True) -> Path:
    pkg = tmp / "android" / "app" / "src" / "main" / "java" / "com" / "example" / "app"
    pkg.mkdir(parents=True)
    if java:
        (pkg / "MainActivity.java").write_text(
            """package com.example.app;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {}
""",
            encoding="utf-8",
        )
    else:
        (pkg / "MainActivity.kt").write_text(
            """package com.example.app

import com.getcapacitor.BridgeActivity

class MainActivity : BridgeActivity()
""",
            encoding="utf-8",
        )
    return tmp / "android"


def test_install_writes_plugin_and_registers_java(tmp_path: Path) -> None:
    android = _scaffold_android(tmp_path)
    actions = install_audio_focus_plugin(android)
    assert any("AudioFocusPlugin.java" in a for a in actions)
    assert any("MainActivity.java" in a for a in actions)

    plugin = (
        android
        / "app"
        / "src"
        / "main"
        / "java"
        / "com"
        / "example"
        / "app"
        / "AudioFocusPlugin.java"
    )
    assert plugin.is_file()
    src = plugin.read_text(encoding="utf-8")
    assert 'name = "AudioFocus"' in src
    assert "requestAudioFocus" in src

    main = find_main_activity(android)
    assert main is not None
    body = main.read_text(encoding="utf-8")
    assert "registerPlugin(AudioFocusPlugin.class);" in body
    assert "super.onCreate" in body
    # Cap requires registerPlugin before super.onCreate
    assert body.index("registerPlugin(AudioFocusPlugin.class)") < body.index("super.onCreate")


def test_install_is_idempotent(tmp_path: Path) -> None:
    android = _scaffold_android(tmp_path)
    first = install_audio_focus_plugin(android)
    second = install_audio_focus_plugin(android)
    assert first
    assert second == []


def test_kotlin_empty_main_activity_registers(tmp_path: Path) -> None:
    android = _scaffold_android(tmp_path, java=False)
    actions = install_audio_focus_plugin(android)
    assert any("MainActivity.kt" in a for a in actions)
    main = find_main_activity(android)
    assert main is not None
    body = main.read_text(encoding="utf-8")
    assert "registerPlugin(AudioFocusPlugin::class.java)" in body
    assert body.index("registerPlugin") < body.index("super.onCreate")
