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


def haptics_impact(*, style: ImpactStyle = "MEDIUM") -> rx.event.EventSpec:
    """Trigger a haptic impact."""
    return call_bridge_void("hapticsImpact", {"style": style})


def haptics_notification(*, type: NotificationStyle = "SUCCESS") -> rx.event.EventSpec:
    """Trigger a haptic notification pattern."""
    return call_bridge_void("hapticsNotification", {"type": type})


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
