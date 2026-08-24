"""Capacitor plugin registry, npm dependency wiring, and Android permission helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Final, TypeAlias

from reflex_capacitor.config import slugify

PluginId: TypeAlias = str

# Short plugin id (CapacitorPlugin.plugins) → @capacitor/* npm package name.
CAPACITOR_PLUGIN_PACKAGES: Final[dict[PluginId, str]] = {
    "local-notifications": "@capacitor/local-notifications",
    "clipboard": "@capacitor/clipboard",
    "haptics": "@capacitor/haptics",
    "share": "@capacitor/share",
    "status-bar": "@capacitor/status-bar",
    "app": "@capacitor/app",
    "splash-screen": "@capacitor/splash-screen",
    "toast": "@capacitor/toast",
    "device": "@capacitor/device",
    "network": "@capacitor/network",
    "keyboard": "@capacitor/keyboard",
    "preferences": "@capacitor/preferences",
    "filesystem": "@capacitor/filesystem",
    "camera": "@capacitor/camera",
    "geolocation": "@capacitor/geolocation",
    "browser": "@capacitor/browser",
    "push-notifications": "@capacitor/push-notifications",
}

# Bundled with every app unless CapacitorPlugin.plugins overrides the tuple.
CORE_PLUGIN_IDS: Final[tuple[PluginId, ...]] = (
    "local-notifications",
    "clipboard",
    "haptics",
    "share",
    "status-bar",
    "app",
    "splash-screen",
    "toast",
    "device",
    "network",
)

# Optional plugins — camera, storage, location, etc.
EXTENDED_PLUGIN_IDS: Final[tuple[PluginId, ...]] = (
    "preferences",
    "camera",
    "geolocation",
    "keyboard",
    "browser",
    "filesystem",
)

# Core + extended; used by the repo demo (rxconfig.py).
ALL_PLUGIN_IDS: Final[tuple[PluginId, ...]] = CORE_PLUGIN_IDS + EXTENDED_PLUGIN_IDS

_ANDROID_PERMISSION_POST_NOTIFICATIONS: Final = "android.permission.POST_NOTIFICATIONS"
_ANDROID_PERMISSION_VIBRATE: Final = "android.permission.VIBRATE"
_ANDROID_PERMISSION_CAMERA: Final = "android.permission.CAMERA"
_ANDROID_PERMISSION_READ_MEDIA_IMAGES: Final = "android.permission.READ_MEDIA_IMAGES"
_ANDROID_PERMISSION_READ_EXTERNAL_STORAGE: Final = "android.permission.READ_EXTERNAL_STORAGE"
_ANDROID_PERMISSION_WRITE_EXTERNAL_STORAGE: Final = "android.permission.WRITE_EXTERNAL_STORAGE"
_ANDROID_PERMISSION_FINE_LOCATION: Final = "android.permission.ACCESS_FINE_LOCATION"
_ANDROID_PERMISSION_COARSE_LOCATION: Final = "android.permission.ACCESS_COARSE_LOCATION"

__all__ = [
    "ALL_PLUGIN_IDS",
    "CAPACITOR_PLUGIN_PACKAGES",
    "CORE_PLUGIN_IDS",
    "EXTENDED_PLUGIN_IDS",
    "PluginId",
    "apply_package_json_deps",
    "copy_plugin_vendor_scripts",
    "ensure_android_camera_permissions",
    "ensure_android_location_permissions",
    "ensure_android_notification_permission",
    "ensure_android_permissions",
    "ensure_android_vibrate_permission",
    "resolve_plugin_ids",
    "vendor_script_filename",
]


def vendor_script_filename(plugin_id: PluginId) -> str:
    """Return the vendor JS filename copied into ``www/assets/reflex-capacitor/vendor/``."""
    package_name = CAPACITOR_PLUGIN_PACKAGES[plugin_id].rsplit("/", maxsplit=1)[-1]
    return f"{package_name}.plugin.js"


def resolve_plugin_ids(plugin_ids: tuple[PluginId, ...]) -> tuple[PluginId, ...]:
    """Validate plugin short names.

    Args:
        plugin_ids: Tuple of Capacitor plugin short ids.

    Returns:
        The same tuple when every id is registered.

    Raises:
        ValueError: If an unknown plugin id is requested.
    """
    unknown = [pid for pid in plugin_ids if pid not in CAPACITOR_PLUGIN_PACKAGES]
    if unknown:
        known = sorted(CAPACITOR_PLUGIN_PACKAGES)
        msg = f"reflex-capacitor: unknown plugin(s) {unknown!r}; known: {known}"
        raise ValueError(msg)
    return plugin_ids


def apply_package_json_deps(
    package_json_path: Path | str,
    plugin_ids: tuple[PluginId, ...],
    *,
    capacitor_version: str,
) -> None:
    """Merge Capacitor core and selected plugin npm deps into ``package.json``.

    Args:
        package_json_path: Path to ``capacitor/package.json``.
        plugin_ids: Plugin short ids to install.
        capacitor_version: Semver range for ``@capacitor/*`` packages.
    """
    path = Path(package_json_path)
    if path.is_file():
        package = json.loads(path.read_text(encoding="utf-8"))
    else:
        package = {"name": "reflex-capacitor-app", "version": "0.1.0", "private": True}

    dependencies = package.setdefault("dependencies", {})
    dev_dependencies = package.setdefault("devDependencies", {})
    dependencies["@capacitor/core"] = capacitor_version
    dependencies["@capacitor/android"] = capacitor_version
    dependencies["@capacitor/ios"] = capacitor_version
    dev_dependencies["@capacitor/cli"] = capacitor_version

    for plugin_id in plugin_ids:
        dependencies[CAPACITOR_PLUGIN_PACKAGES[plugin_id]] = capacitor_version

    if package.get("name") in (None, "reflex-capacitor-app"):
        package["name"] = slugify(str(package.get("name", "reflex-capacitor-app")))

    path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")


def copy_plugin_vendor_scripts(
    capacitor_root: Path | str,
    web_root: Path | str,
    plugin_ids: tuple[PluginId, ...],
) -> None:
    """Copy ``capacitor.js`` and plugin bundles into the static export tree.

    Must run after ``npm install`` in ``capacitor_root`` so ``node_modules`` exists.

    Args:
        capacitor_root: Capacitor project root (contains ``node_modules/``).
        web_root: Reflex static export directory (Capacitor ``webDir``).
        plugin_ids: Plugin short ids whose ``plugin.js`` files should be copied.
    """
    cap_root = Path(capacitor_root).resolve()
    www_dir = Path(web_root).resolve()
    vendor_dir = www_dir / "assets" / "reflex-capacitor" / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    core_js = cap_root / "node_modules" / "@capacitor" / "core" / "dist" / "capacitor.js"
    if not core_js.is_file():
        msg = f"reflex-capacitor: missing {core_js} — run npm install in {cap_root}"
        raise FileNotFoundError(msg)
    shutil.copyfile(core_js, vendor_dir / "capacitor.js")

    for plugin_id in plugin_ids:
        npm_package = CAPACITOR_PLUGIN_PACKAGES[plugin_id]
        plugin_js = cap_root / "node_modules" / npm_package / "dist" / "plugin.js"
        if not plugin_js.is_file():
            msg = (
                f"reflex-capacitor: missing {plugin_js} — "
                f"add {npm_package!r} to CapacitorPlugin.plugins"
            )
            raise FileNotFoundError(msg)
        shutil.copyfile(plugin_js, vendor_dir / vendor_script_filename(plugin_id))


def ensure_android_notification_permission(manifest_path: Path | str) -> None:
    """Add ``POST_NOTIFICATIONS`` for Android 13+ local notifications."""
    _ensure_android_permission(manifest_path, _ANDROID_PERMISSION_POST_NOTIFICATIONS)


def ensure_android_vibrate_permission(manifest_path: Path | str) -> None:
    """Add ``VIBRATE`` for Capacitor Haptics on Android."""
    _ensure_android_permission(manifest_path, _ANDROID_PERMISSION_VIBRATE)


def ensure_android_camera_permissions(manifest_path: Path | str) -> None:
    """Add camera and gallery permissions for ``@capacitor/camera``."""
    ensure_android_permissions(
        manifest_path,
        (
            _ANDROID_PERMISSION_CAMERA,
            _ANDROID_PERMISSION_READ_MEDIA_IMAGES,
            _ANDROID_PERMISSION_READ_EXTERNAL_STORAGE,
            _ANDROID_PERMISSION_WRITE_EXTERNAL_STORAGE,
        ),
    )


def ensure_android_location_permissions(manifest_path: Path | str) -> None:
    """Add location permissions for ``@capacitor/geolocation``."""
    ensure_android_permissions(
        manifest_path,
        (
            _ANDROID_PERMISSION_FINE_LOCATION,
            _ANDROID_PERMISSION_COARSE_LOCATION,
        ),
    )


def ensure_android_permissions(manifest_path: Path | str, permissions: tuple[str, ...]) -> None:
    """Add multiple Android ``uses-permission`` entries when missing."""
    for permission in permissions:
        _ensure_android_permission(manifest_path, permission)


def _ensure_android_permission(manifest_path: Path | str, permission: str) -> None:
    """Insert a ``uses-permission`` line if missing from ``AndroidManifest.xml``."""
    path = Path(manifest_path)
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8")
    if permission in text:
        return

    permission_line = f'    <uses-permission android:name="{permission}" />\n'
    if "<manifest" in text and "<uses-permission" not in text:
        lines = text.splitlines(keepends=True)
        output: list[str] = []
        inserted = False
        for line in lines:
            output.append(line)
            if not inserted and line.strip().startswith("<manifest"):
                output.append("\n")
                output.append(permission_line)
                inserted = True
        if inserted:
            path.write_text("".join(output), encoding="utf-8")
            return

    if "</manifest>" in text:
        path.write_text(text.replace("</manifest>", permission_line + "</manifest>", count=1), encoding="utf-8")
