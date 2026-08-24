"""Server-side logging helpers for bridge debugging."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("reflex_capacitor.bridge")

_MAX_PREVIEW = 240


def _preview(value: Any) -> str:
    """Return a compact string for log lines and UI."""
    if value is None:
        return "null"
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = repr(value)
    if len(text) > _MAX_PREVIEW:
        return text[: _MAX_PREVIEW - 3] + "..."
    return text


def log_bridge(
    method: str,
    *,
    args: dict[str, Any] | None = None,
    result: Any = None,
    error: str | None = None,
    source: str = "server",
) -> str:
    """Log a bridge-related event and return a one-line summary for UI display.

    Configure the logger in your app (or rely on Reflex defaults)::

        logging.getLogger("reflex_capacitor.bridge").setLevel(logging.DEBUG)

    Backend ``reflex run`` output will then show bridge callback / diagnostic lines.
    """
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    parts = [f"[{ts}]", f"({source})", method]
    if args:
        parts.append(f"args={_preview(args)}")
    if error:
        parts.append(f"ERROR={error}")
    elif result is not None:
        parts.append(f"result={_preview(result)}")
    line = " ".join(parts)
    if error:
        logger.error(line)
    else:
        logger.info(line)
    return line
