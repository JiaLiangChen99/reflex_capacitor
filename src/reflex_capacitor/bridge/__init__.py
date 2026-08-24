"""Reflex ↔ Capacitor native bridge (Python API + JS assets + injection)."""

from reflex_capacitor.bridge import api as mobile

from . import api
from .inject import install_bridge
from .log import log_bridge
from .plugins import (
    DEFAULT_PLUGINS,
    PLUGIN_PACKAGES,
    apply_package_json_deps,
    copy_vendor_scripts,
    ensure_android_notification_permission,
    resolve_plugins,
)

__all__ = [
    "DEFAULT_PLUGINS",
    "PLUGIN_PACKAGES",
    "api",
    "mobile",
    "install_bridge",
    "log_bridge",
    "apply_package_json_deps",
    "copy_vendor_scripts",
    "ensure_android_notification_permission",
    "resolve_plugins",
]
