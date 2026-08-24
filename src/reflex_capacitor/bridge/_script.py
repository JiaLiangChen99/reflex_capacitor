"""Helpers for generating rx.call_script snippets targeting __REFLEX_CAPACITOR__."""

from __future__ import annotations

import json
from typing import Any

import reflex as rx


def call_bridge(
    method: str,
    args: dict[str, Any] | None = None,
    *,
    callback: Any = None,
) -> rx.event.EventSpec:
    """Call an async method on ``window.__REFLEX_CAPACITOR__``.

    Args:
        method: Bridge method name (e.g. ``"notify"``).
        args: JSON-serializable arguments object passed to the method.
        callback: Optional Reflex handler for the resolved return value.

    Returns:
        A Reflex event that runs the bridge call in the webview.
    """
    payload = json.dumps(args or {})
    script = (
        "(async () => {"
        "  const b = window.__REFLEX_CAPACITOR__;"
        "  if (!b) {"
        "    console.warn('reflex-capacitor: bridge not loaded');"
        "    return { ok: false, error: 'bridge_not_loaded' };"
        "  }"
        "  try {"
        f"    return await b.{method}({payload});"
        "  } catch (e) {"
        "    console.error('reflex-capacitor: bridge call failed', e);"
        "    return { ok: false, error: String(e) };"
        "  }"
        "})()"
    )
    return rx.call_script(script, callback=callback)


def call_bridge_void(method: str, args: dict[str, Any] | None = None) -> rx.event.EventSpec:
    """Call a bridge method without using the return value."""
    return call_bridge(method, args)
