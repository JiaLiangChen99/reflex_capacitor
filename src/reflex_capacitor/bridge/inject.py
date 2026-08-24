"""Inject reflex-capacitor bridge scripts into the exported index.html."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .plugins import PLUGIN_VENDOR_FILE

_BRIDGE_BEGIN = "<!-- reflex-capacitor bridge begin -->"
_BRIDGE_END = "<!-- reflex-capacitor bridge end -->"
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_BRIDGE_JS = "bridge.js"
_WWW_BRIDGE = Path("assets") / "reflex-capacitor" / _BRIDGE_JS
_VENDOR_PREFIX = "./assets/reflex-capacitor/vendor/"


def bridge_asset_dir() -> Path:
    """Return the packaged bridge assets directory."""
    return _ASSETS_DIR


def copy_bridge_js(www_dir: Path) -> None:
    """Copy bridge.js from the package into www/assets/reflex-capacitor/."""
    dest_dir = www_dir / "assets" / "reflex-capacitor"
    dest_dir.mkdir(parents=True, exist_ok=True)
    src = _ASSETS_DIR / _BRIDGE_JS
    if not src.is_file():
        msg = f"reflex-capacitor: missing bridge asset at {src}"
        raise FileNotFoundError(msg)
    shutil.copyfile(src, dest_dir / _BRIDGE_JS)


def build_bridge_snippet(plugins: tuple[str, ...]) -> str:
    """Build HTML script tags for Capacitor core, plugins, and the bridge."""
    lines = [_BRIDGE_BEGIN]
    lines.append(f'    <script src="{_VENDOR_PREFIX}capacitor.js"></script>')
    for short in plugins:
        vendor_file = PLUGIN_VENDOR_FILE[short]
        lines.append(f'    <script src="{_VENDOR_PREFIX}{vendor_file}"></script>')
    lines.append(f'    <script src="./{_WWW_BRIDGE.as_posix()}"></script>')
    lines.append(f"    {_BRIDGE_END}")
    return "\n".join(lines) + "\n"


def inject_index_html(www_dir: Path, plugins: tuple[str, ...]) -> None:
    """Idempotently inject bridge script tags before </body> in index.html."""
    index = www_dir / "index.html"
    if not index.is_file():
        # SPA fallback export may only have __spa-fallback.html
        for candidate in ("__spa-fallback.html", "index.html"):
            path = www_dir / candidate
            if path.is_file():
                index = path
                break
        else:
            return

    text = index.read_text(encoding="utf-8")
    snippet = build_bridge_snippet(plugins)

    if _BRIDGE_BEGIN in text:
        text = re.sub(
            rf"{re.escape(_BRIDGE_BEGIN)}.*?{re.escape(_BRIDGE_END)}\n?",
            snippet,
            text,
            count=1,
            flags=re.DOTALL,
        )
    elif re.search(r"</body>", text, flags=re.IGNORECASE):
        text = re.sub(r"</body>", snippet + "</body>", text, count=1, flags=re.IGNORECASE)
    else:
        text = text.rstrip() + "\n" + snippet

    index.write_text(text, encoding="utf-8")


def install_bridge(www_dir: Path, plugins: tuple[str, ...]) -> None:
    """Copy bridge.js and patch index.html (vendor copies happen after npm install)."""
    www_dir = Path(www_dir).resolve()
    copy_bridge_js(www_dir)
    inject_index_html(www_dir, plugins)
