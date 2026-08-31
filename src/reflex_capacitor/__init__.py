"""Package a Reflex app as a Capacitor mobile app (remote backend)."""

from .bridge import api as mobile
from .bridge import api  # noqa: F401 — re-export module for `from reflex_capacitor.bridge import api`
from . import components
from .plugin import CapacitorPlugin as CapacitorPlugin
from .urls import get_upload_url, resolve_backend_base

__all__ = [
    "CapacitorPlugin",
    "mobile",
    "api",
    "components",
    "get_upload_url",
    "resolve_backend_base",
]
