"""Shared defaults and helpers for reflex-capacitor."""

from __future__ import annotations

import re

# Capacitor project directory relative to the app root (holds package.json, www/, android/).
DEFAULT_CAPACITOR_DIR = "capacitor"

# Static assets folder name inside the Capacitor project (capacitor.config webDir).
DEFAULT_WEB_DIR = "www"

# Dev-mode override consumed while compiling the frontend (mirrors reflex-desktop).
DEV_BACKEND_URL_ENV = "REFLEX_CAPACITOR_DEV_BACKEND_URL"

# WebView origins Capacitor commonly serves the bundled frontend from.
CAPACITOR_ORIGINS = (
    "capacitor://localhost",
    "http://localhost",
    "https://localhost",
)

# Pinned Capacitor major line for generated package.json.
CAPACITOR_VERSION = "^7.0.0"


def slugify(name: str) -> str:
    """Turn a product name into a lowercase npm / filesystem-safe slug.

    Args:
        name: Human-readable product name.

    Returns:
        A lowercase hyphen-separated slug.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "reflex-app"


def default_app_id(app_name: str) -> str:
    """Derive a reverse-DNS app id from the Reflex app name.

    Args:
        app_name: Reflex ``config.app_name``.

    Returns:
        An identifier like ``dev.reflex.myapp``.
    """
    safe = re.sub(r"[^a-z0-9]", "", app_name.lower()) or "app"
    return f"dev.reflex.{safe}"
