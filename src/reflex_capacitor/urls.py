"""URL helpers that honor Capacitor remote ``backend_url`` (not localhost).

``rx.get_upload_url`` compiles to ``getBackendURL(env.UPLOAD)+...``. That is correct
when the frontend ``env`` was baked with the LAN/API host. Event handlers that build
Python strings via ``Endpoint.UPLOAD.get_url()`` still use ``config.api_url``, which
is often ``http://localhost:8000`` on the PC — useless inside a phone WebView.

Use :func:`get_upload_url` / :func:`resolve_backend_base` so Cap apps resolve the
same base as ``CapacitorPlugin`` (env → plugin.backend_url → api_url).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .config import DEV_BACKEND_URL_ENV

if TYPE_CHECKING:
    pass

__all__ = [
    "get_upload_url",
    "resolve_backend_base",
]


def resolve_backend_base() -> str:
    """Return the Reflex backend origin for Capacitor clients.

    Resolution order:

    1. ``REFLEX_CAPACITOR_DEV_BACKEND_URL`` (CLI ``dev`` / CI sync bake)
    2. ``CapacitorPlugin.backend_url`` from ``rxconfig``
    3. ``config.api_url`` (Reflex default, often localhost)
    """
    if dev := os.environ.get(DEV_BACKEND_URL_ENV):
        return dev.rstrip("/")

    from reflex_base.config import get_config

    from .plugin import CapacitorPlugin

    cfg = get_config()
    for plugin in getattr(cfg, "plugins", []) or []:
        if isinstance(plugin, CapacitorPlugin) and plugin.backend_url:
            return plugin.backend_url.rstrip("/")

    return str(cfg.api_url).rstrip("/")


def get_upload_url(file_path: str) -> str:
    """Absolute ``/_upload/<file>`` URL using :func:`resolve_backend_base`.

    Drop-in for Cap shells instead of ``rx.get_upload_url`` when you need a real
    host (``rx.el.video`` / ``rx.el.audio`` ``src``, or ``mobile.play_recording``).

    Args:
        file_path: Filename under ``rx.get_upload_dir()`` (e.g. ``sample.mp3``).
    """
    from reflex.constants import Endpoint
    from reflex_base.config import get_config

    name = str(file_path).lstrip("/")
    base = resolve_backend_base()
    upload_path = get_config().prepend_backend_path(str(Endpoint.UPLOAD)).rstrip("/")
    return f"{base}{upload_path}/{name}"
