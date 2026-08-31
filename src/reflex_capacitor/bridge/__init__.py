"""Reflex ↔ Capacitor native bridge (Python API + JS assets + injection)."""

from reflex_capacitor.bridge import api as mobile

from . import api
from .inject import install_bridge
from .log import log_bridge
from .plugins import (
    ALL_PLUGIN_IDS,
    BUILTIN_BRIDGE_PLUGIN_IDS,
    CAPACITOR_PLUGIN_PACKAGES,
    CORE_PLUGIN_IDS,
    EXTENDED_PLUGIN_IDS,
    apply_package_json_deps,
    copy_plugin_vendor_scripts,
    ensure_android_notification_permission,
    has_npm_package,
    resolve_plugin_ids,
    vendor_script_filename,
)

__all__ = [
    "ALL_PLUGIN_IDS",
    "BUILTIN_BRIDGE_PLUGIN_IDS",
    "CAPACITOR_PLUGIN_PACKAGES",
    "CORE_PLUGIN_IDS",
    "EXTENDED_PLUGIN_IDS",
    "api",
    "mobile",
    "install_bridge",
    "log_bridge",
    "apply_package_json_deps",
    "copy_plugin_vendor_scripts",
    "ensure_android_notification_permission",
    "has_npm_package",
    "resolve_plugin_ids",
    "vendor_script_filename",
]
