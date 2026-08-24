"""Capacitor npm package names keyed by short plugin id."""

from __future__ import annotations

from reflex_capacitor.config import CAPACITOR_VERSION

# Short id (used in CapacitorPlugin.plugins) → npm package name.
PLUGIN_PACKAGES: dict[str, str] = {
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

# P0 defaults for Phase 2 (see docs/02-native-bridge.md).
DEFAULT_PLUGINS: tuple[str, ...] = (
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

# Vendor script filename stem (plugin.js copies) per short id.
PLUGIN_VENDOR_FILE: dict[str, str] = {
    short: pkg.rsplit("/", 1)[-1] + ".plugin.js" for short, pkg in PLUGIN_PACKAGES.items()
}


def resolve_plugins(plugins: tuple[str, ...]) -> tuple[str, ...]:
    """Validate plugin short names.

    Args:
        plugins: Tuple of short plugin ids.

    Returns:
        The same tuple if every id is known.

    Raises:
        ValueError: If an unknown plugin id is requested.
    """
    unknown = [p for p in plugins if p not in PLUGIN_PACKAGES]
    if unknown:
        msg = f"reflex-capacitor: unknown plugin(s) {unknown!r}; known: {sorted(PLUGIN_PACKAGES)}"
        raise ValueError(msg)
    return plugins


def apply_package_json_deps(pkg_path, plugins: tuple[str, ...], *, capacitor_version: str) -> None:
    """Merge Capacitor core + selected plugin npm deps into package.json.

    Args:
        pkg_path: Path to capacitor/package.json.
        plugins: Short plugin ids to install.
        capacitor_version: Semver range for @capacitor/* packages.
    """
    import json
    from pathlib import Path

    from reflex_capacitor.config import slugify

    path = Path(pkg_path)
    if path.exists():
        pkg = json.loads(path.read_text(encoding="utf-8"))
    else:
        pkg = {"name": "reflex-capacitor-app", "version": "0.1.0", "private": True}

    deps = pkg.setdefault("dependencies", {})
    dev_deps = pkg.setdefault("devDependencies", {})
    deps["@capacitor/core"] = capacitor_version
    deps["@capacitor/android"] = capacitor_version
    deps["@capacitor/ios"] = capacitor_version
    dev_deps["@capacitor/cli"] = capacitor_version

    for short in plugins:
        deps[PLUGIN_PACKAGES[short]] = capacitor_version

    if "name" not in pkg or pkg["name"] == "reflex-capacitor-app":
        pkg["name"] = slugify(pkg.get("name", "reflex-capacitor-app"))

    path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")


def copy_vendor_scripts(cap_root, www_dir, plugins: tuple[str, ...]) -> None:
    """Copy capacitor.js + plugin.js bundles into www for the static bridge.

    Must run after ``npm install`` in ``cap_root`` so node_modules exists.

    Args:
        cap_root: Capacitor project root (holds node_modules/).
        www_dir: Reflex static export directory inside the Cap project.
        plugins: Short plugin ids to copy.
    """
    import shutil
    from pathlib import Path

    cap_root = Path(cap_root).resolve()
    www_dir = Path(www_dir).resolve()
    vendor = www_dir / "assets" / "reflex-capacitor" / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)

    core_js = cap_root / "node_modules" / "@capacitor" / "core" / "dist" / "capacitor.js"
    if not core_js.is_file():
        msg = f"reflex-capacitor: missing {core_js} — run npm install in {cap_root}"
        raise FileNotFoundError(msg)
    shutil.copyfile(core_js, vendor / "capacitor.js")

    for short in plugins:
        pkg = PLUGIN_PACKAGES[short]
        plugin_js = cap_root / "node_modules" / pkg / "dist" / "plugin.js"
        if not plugin_js.is_file():
            msg = f"reflex-capacitor: missing {plugin_js} — add {pkg} to CapacitorPlugin.plugins"
            raise FileNotFoundError(msg)
        dest_name = PLUGIN_VENDOR_FILE[short]
        shutil.copyfile(plugin_js, vendor / dest_name)


def ensure_android_notification_permission(manifest_path) -> None:
    """Add POST_NOTIFICATIONS for Android 13+ local notifications."""
    from pathlib import Path

    path = Path(manifest_path)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    perm = 'android.permission.POST_NOTIFICATIONS'
    if perm in text:
        return
    insert = f'    <uses-permission android:name="{perm}" />\n'
    if "<manifest" in text and "<uses-permission" not in text:
        text = text.replace("<manifest", "<manifest", 1)
        # After opening manifest tag line
        lines = text.splitlines(keepends=True)
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.strip().startswith("<manifest"):
                out.append("\n")
                out.append(insert)
                inserted = True
        if inserted:
            path.write_text("".join(out), encoding="utf-8")
