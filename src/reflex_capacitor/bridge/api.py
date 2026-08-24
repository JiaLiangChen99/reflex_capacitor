"""Python → Capacitor bridge API for Reflex event handlers.

Usage::

    import reflex as rx
    from reflex_capacitor import mobile

    rx.button("Notify", on_click=mobile.notify("Hello", "From Reflex"))
    rx.button("Share", on_click=mobile.share(text="Check this out"))
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx

from ._script import call_bridge, call_bridge_void

ImpactStyle = Literal["HEAVY", "MEDIUM", "LIGHT"]
NotificationStyle = Literal["SUCCESS", "WARNING", "ERROR"]
StatusBarStyle = Literal["DARK", "LIGHT", "DEFAULT"]
ToastDuration = Literal["short", "long"]


def notify(title: str, body: str = "") -> rx.event.EventSpec:
    """Show a local OS notification (requires Local Notifications plugin)."""
    return call_bridge_void("notify", {"title": title, "body": body})


def toast(text: str, *, duration: ToastDuration = "short") -> rx.event.EventSpec:
    """Show a native toast banner."""
    return call_bridge_void("toast", {"text": text, "duration": duration})


def haptics_impact(*, style: ImpactStyle = "MEDIUM", callback: Any = None) -> rx.event.EventSpec:
    """Trigger a haptic impact (very short tick — may be hard to feel on some Android phones)."""
    return call_bridge("hapticsImpact", {"style": style}, callback=callback)


def haptics_notification(*, type: NotificationStyle = "SUCCESS", callback: Any = None) -> rx.event.EventSpec:
    """Trigger a haptic notification pattern (slightly longer than impact)."""
    return call_bridge("hapticsNotification", {"type": type}, callback=callback)


def haptics_vibrate(*, duration_ms: int = 300, callback: Any = None) -> rx.event.EventSpec:
    """Vibrate for ``duration_ms`` — more noticeable than impact for testing."""
    return call_bridge("hapticsVibrate", {"duration": duration_ms}, callback=callback)


def share(
    *,
    title: str | None = None,
    text: str | None = None,
    url: str | None = None,
    dialog_title: str | None = None,
) -> rx.event.EventSpec:
    """Open the system share sheet."""
    args: dict[str, str] = {}
    if title is not None:
        args["title"] = title
    if text is not None:
        args["text"] = text
    if url is not None:
        args["url"] = url
    if dialog_title is not None:
        args["dialogTitle"] = dialog_title
    return call_bridge_void("share", args)


def clipboard_write(text: str) -> rx.event.EventSpec:
    """Write text to the system clipboard."""
    return call_bridge_void("clipboardWrite", {"text": text})


def clipboard_read(callback: Any) -> rx.event.EventSpec:
    """Read clipboard text and pass ``{value: str}`` to the callback handler."""
    return call_bridge("clipboardRead", callback=callback)


def status_bar_set_style(*, style: StatusBarStyle = "DARK") -> rx.event.EventSpec:
    """Set the status bar icon/text style."""
    return call_bridge_void("statusBarSetStyle", {"style": style})


def status_bar_hide() -> rx.event.EventSpec:
    """Hide the status bar."""
    return call_bridge_void("statusBarHide")


def status_bar_show() -> rx.event.EventSpec:
    """Show the status bar."""
    return call_bridge_void("statusBarShow")


def splash_hide() -> rx.event.EventSpec:
    """Hide the splash screen after the app has loaded."""
    return call_bridge_void("splashHide")


def device_info(callback: Any) -> rx.event.EventSpec:
    """Fetch device info and pass the result to the callback handler."""
    return call_bridge("deviceInfo", callback=callback)


def network_status(callback: Any) -> rx.event.EventSpec:
    """Fetch network status and pass the result to the callback handler."""
    return call_bridge("networkStatus", callback=callback)


def app_exit() -> rx.event.EventSpec:
    """Exit the app (platform-dependent)."""
    return call_bridge_void("appExit")


def diagnostics(callback: Any) -> rx.event.EventSpec:
    """Fetch bridge diagnostics (platform, loaded plugins, log count)."""
    return call_bridge("getDiagnostics", callback=callback)


def bridge_logs(limit: int = 50, callback: Any = None) -> rx.event.EventSpec:
    """Fetch recent client-side bridge log entries from the WebView."""
    return call_bridge("getLogs", {"limit": limit}, callback=callback)


def clear_logs() -> rx.event.EventSpec:
    """Clear the in-WebView bridge log buffer."""
    return call_bridge_void("clearLogs")


# --- Phase 3 P1 ---


def pref_set(key: str, value: str, *, callback: Any = None) -> rx.event.EventSpec:
    """Store a string in Capacitor Preferences (device-local key/value)."""
    return call_bridge("prefSet", {"key": key, "value": value}, callback=callback)


def pref_get(key: str, callback: Any) -> rx.event.EventSpec:
    """Read a Preferences value; callback receives ``{key, value}``."""
    return call_bridge("prefGet", {"key": key}, callback=callback)


def take_photo(callback: Any, *, quality: int = 90) -> rx.event.EventSpec:
    """Capture a photo; callback receives ``{dataUrl, format}`` (not a file path)."""
    return call_bridge("takePhoto", {"quality": quality}, callback=callback)


def pick_images(callback: Any, *, limit: int = 1, quality: int = 90) -> rx.event.EventSpec:
    """Pick images from the gallery; callback receives ``{photos: [...]}``."""
    return call_bridge("pickImages", {"limit": limit, "quality": quality}, callback=callback)


def get_current_position(callback: Any, *, enable_high_accuracy: bool = True) -> rx.event.EventSpec:
    """Get GPS coordinates; callback receives lat/lon/accuracy."""
    return call_bridge(
        "getCurrentPosition",
        {"enableHighAccuracy": enable_high_accuracy},
        callback=callback,
    )


def keyboard_show(*, callback: Any = None) -> rx.event.EventSpec:
    """Show the soft keyboard."""
    return call_bridge("keyboardShow", callback=callback)


def keyboard_hide(*, callback: Any = None) -> rx.event.EventSpec:
    """Hide the soft keyboard."""
    return call_bridge("keyboardHide", callback=callback)


def browser_open(url: str, *, callback: Any = None) -> rx.event.EventSpec:
    """Open a URL in the in-app browser (SFSafariViewController / Custom Tabs)."""
    return call_bridge("browserOpen", {"url": url}, callback=callback)


def fs_write(
    path: str,
    data: str,
    *,
    directory: str = "DATA",
    callback: Any = None,
) -> rx.event.EventSpec:
    """Write UTF-8 text to the app sandbox (Capacitor Filesystem directory)."""
    return call_bridge("fsWrite", {"path": path, "data": data, "directory": directory}, callback=callback)


def fs_read(path: str, callback: Any, *, directory: str = "DATA") -> rx.event.EventSpec:
    """Read UTF-8 text from the app sandbox."""
    return call_bridge("fsRead", {"path": path, "directory": directory}, callback=callback)


def invoke(
    plugin: str,
    method: str,
    args: dict[str, Any] | None = None,
    *,
    callback: Any = None,
) -> rx.event.EventSpec:
    """Call a Capacitor plugin method directly (extension point for custom plugins)."""
    return call_bridge(
        "invoke",
        {"plugin": plugin, "method": method, "args": args or {}},
        callback=callback,
    )
