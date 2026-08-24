"""Tests for Android release signing helpers."""

from __future__ import annotations

from pathlib import Path

from reflex_capacitor.android_signing import (
    patch_app_build_gradle,
    write_keystore_properties,
)
from reflex_capacitor.android_signing import AndroidSigningConfig as Signing


def _sample_build_gradle() -> str:
    return """
plugins {
    id 'com.android.application'
}

android {
    namespace "dev.reflex.demo"
    compileSdkVersion rootProject.ext.compileSdkVersion
    defaultConfig {
        applicationId "dev.reflex.demo"
        minSdkVersion rootProject.ext.minSdkVersion
    }
    buildTypes {
        release {
            minifyEnabled false
        }
        debug {
            debuggable true
        }
    }
}
""".strip()


def test_patch_app_build_gradle_idempotent(tmp_path: Path):
    gradle = tmp_path / "build.gradle"
    gradle.write_text(_sample_build_gradle(), encoding="utf-8")
    patch_app_build_gradle(gradle)
    first = gradle.read_text(encoding="utf-8")
    assert "reflex-capacitor signing begin" in first
    assert "signingConfig signingConfigs.release" in first
    patch_app_build_gradle(gradle)
    assert gradle.read_text(encoding="utf-8") == first


def test_write_keystore_properties_relative_path(tmp_path: Path):
    android_root = tmp_path / "android"
    android_root.mkdir()
    keystore = android_root / "keys" / "release.keystore"
    keystore.parent.mkdir()
    keystore.write_bytes(b"fake")
    signing = Signing(
        keystore_path=keystore,
        keystore_password="store-pass",
        key_alias="myalias",
        key_password="key-pass",
    )
    props = write_keystore_properties(android_root, signing)
    text = props.read_text(encoding="utf-8")
    assert "storeFile=keys/release.keystore" in text
    assert "keyAlias=myalias" in text
