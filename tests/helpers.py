"""Offline test helpers (fake export tree, node_modules, Android manifest)."""

from __future__ import annotations

from pathlib import Path

from reflex_capacitor.bridge.plugins import CAPACITOR_PLUGIN_PACKAGES


def seed_static_export(static_dir: Path) -> None:
    """Write a minimal Reflex export tree under ``static_dir``."""
    static_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>app</div></body></html>\n",
        encoding="utf-8",
    )
    assets = static_dir / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "app.js").write_text("// export bundle stub\n", encoding="utf-8")


def seed_fake_node_modules(cap_root: Path, plugin_ids: tuple[str, ...]) -> None:
    """Create stub ``node_modules/@capacitor/*`` trees for vendor copy tests."""
    core_dist = cap_root / "node_modules" / "@capacitor" / "core" / "dist"
    core_dist.mkdir(parents=True, exist_ok=True)
    (core_dist / "capacitor.js").write_text("// stub capacitor core\n", encoding="utf-8")

    for plugin_id in plugin_ids:
        if plugin_id not in CAPACITOR_PLUGIN_PACKAGES:
            continue
        npm_package = CAPACITOR_PLUGIN_PACKAGES[plugin_id]
        plugin_dist = cap_root / "node_modules" / npm_package / "dist"
        plugin_dist.mkdir(parents=True, exist_ok=True)
        (plugin_dist / "plugin.js").write_text(
            f"// stub plugin {plugin_id}\n",
            encoding="utf-8",
        )


def seed_android_manifest(cap_root: Path) -> Path:
    """Write a minimal AndroidManifest.xml for permission patch tests."""
    manifest = cap_root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <application android:label="Test">\n'
        '        <activity android:name=".MainActivity" />\n'
        '    </application>\n'
        '</manifest>\n',
        encoding="utf-8",
    )
    return manifest
