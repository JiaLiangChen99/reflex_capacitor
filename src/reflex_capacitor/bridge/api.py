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
BackButtonMode = Literal["emit", "exit", "history"]


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


def platform_info(callback: Any) -> rx.event.EventSpec:
    """Return runtime platform flags from the WebView shell.

    Callback receives::

        {
            "platform": "ios" | "android" | "web",
            "isNative": bool,
            "isAndroid": bool,
            "isIos": bool,
            "isWeb": bool,
        }

    Use this in Reflex State to branch UI or call different ``mobile.*`` handlers.
    """
    return call_bridge("platformInfo", callback=callback)


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


def take_photo(
    callback: Any,
    *,
    quality: int = 90,
    save_to_gallery: bool = False,
) -> rx.event.EventSpec:
    """Capture a photo.

    Callback receives ``{dataUrl, webPath, format, saved, ...}``.

    By default the image stays in memory as ``dataUrl`` (no cloud, not saved to disk).
    Set ``save_to_gallery=True`` to also write into the system photo gallery on
    Android/iOS (local only, no upload).
    """
    return call_bridge(
        "takePhoto",
        {"quality": quality, "saveToGallery": save_to_gallery},
        callback=callback,
    )


def pick_images(callback: Any, *, limit: int = 1, quality: int = 90) -> rx.event.EventSpec:
    """Pick images from the gallery; callback receives ``{photos: [...]}``."""
    return call_bridge("pickImages", {"limit": limit, "quality": quality}, callback=callback)


def get_current_position(
    callback: Any,
    *,
    enable_high_accuracy: bool = False,
    timeout_ms: int = 30000,
) -> rx.event.EventSpec:
    """Get GPS coordinates; callback receives lat/lon/accuracy.

    Defaults to network/coarse first (faster indoors). Set ``enable_high_accuracy=True``
    to prefer GPS (slower, needs clear sky).
    """
    return call_bridge(
        "getCurrentPosition",
        {"enableHighAccuracy": enable_high_accuracy, "timeout": timeout_ms},
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


def start_recording(
    *,
    directory: str | None = None,
    sub_directory: str | None = None,
    callback: Any = None,
) -> rx.event.EventSpec:
    """Start microphone recording (built into packaged ``bridge.js``).

    Enable ``voice-recorder`` in ``CapacitorPlugin.plugins`` so finalize_bridge
    writes Android ``RECORD_AUDIO`` / iOS microphone usage strings.

    ``directory`` / ``sub_directory`` are reserved for future sandbox writes and
    currently ignored (audio is returned as a ``dataUrl`` on stop).
    """
    args: dict[str, Any] = {}
    if directory is not None:
        args["directory"] = directory
    if sub_directory is not None:
        args["subDirectory"] = sub_directory
    return call_bridge("startRecording", args, callback=callback)


def stop_recording(callback: Any) -> rx.event.EventSpec:
    """Stop recording; callback receives ``{ok, dataUrl, mimeType, msDuration, path, ...}``."""
    return call_bridge("stopRecording", callback=callback)


def play_recording(
    *,
    data_url: str | None = None,
    path: str | None = None,
    callback: Any = None,
) -> rx.event.EventSpec:
    """Play the last recording, or an explicit ``data_url`` / filesystem ``path``."""
    args: dict[str, Any] = {}
    if data_url is not None:
        args["dataUrl"] = data_url
    if path is not None:
        args["path"] = path
    return call_bridge("playRecording", args, callback=callback)


def stop_playback(*, callback: Any = None) -> rx.event.EventSpec:
    """Stop in-WebView playback started by :func:`play_recording`."""
    return call_bridge("stopPlayback", callback=callback)


def recording_status(callback: Any) -> rx.event.EventSpec:
    """Return current recorder status (``RECORDING`` / ``PAUSED`` / ``NONE``)."""
    return call_bridge("recordingStatus", callback=callback)


def speak(
    text: str,
    *,
    lang: str = "zh-CN",
    rate: float = 1.0,
    pitch: float = 1.0,
    volume: float = 1.0,
    callback: Any = None,
) -> rx.event.EventSpec:
    """Speak ``text`` with on-device system TTS.

    Prefers the Capacitor ``TextToSpeech`` native plugin when ``text-to-speech``
    is enabled (recommended on Android WebView). Falls back to Web
    ``speechSynthesis`` in browsers that support it.

    Cloud LLM replies should return text only; call this to announce locally.
    """
    return call_bridge(
        "speak",
        {
            "text": text,
            "lang": lang,
            "rate": rate,
            "pitch": pitch,
            "volume": volume,
        },
        callback=callback,
    )


def stop_speak(*, callback: Any = None) -> rx.event.EventSpec:
    """Stop any in-progress :func:`speak` utterance."""
    return call_bridge("stopSpeak", callback=callback)


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


def editor_options(
    *,
    enable_crop: bool = True,
    enable_rotate: bool = True,
    enable_compress: bool = True,
    enable_watermark: bool = False,
    watermark_text: str = "",
    max_width: int = 1920,
    quality: int = 85,
    aspect_ratio: float | None = None,
    save_to_sandbox: bool = False,
    sandbox_path: str = "edited/photo.jpg",
    return_data_url: bool = True,
) -> dict[str, Any]:
    """Build editor option dict for :func:`capture_and_edit` / :func:`edit_image`."""
    from reflex_capacitor.components.image_editor import ImageEditorOptions

    return ImageEditorOptions(
        enable_crop=enable_crop,
        enable_rotate=enable_rotate,
        enable_compress=enable_compress,
        enable_watermark=enable_watermark,
        watermark_text=watermark_text,
        max_width=max_width,
        quality=quality,
        aspect_ratio=aspect_ratio,
        save_to_sandbox=save_to_sandbox,
        sandbox_path=sandbox_path,
        return_data_url=return_data_url,
    ).to_bridge()


def capture_and_edit(
    callback: Any,
    *,
    source: Literal["prompt", "camera", "gallery"] = "prompt",
    editor: dict[str, Any] | None = None,
) -> rx.event.EventSpec:
    """Pick/capture an image then open the built-in editor (device-local processing)."""
    return call_bridge(
        "captureAndEdit",
        {"source": source, "editor": editor or editor_options()},
        callback=callback,
    )


def edit_image(
    callback: Any,
    *,
    data_url: str | None = None,
    web_path: str | None = None,
    editor: dict[str, Any] | None = None,
) -> rx.event.EventSpec:
    """Open the built-in editor for an existing ``dataUrl`` or Capacitor ``webPath``."""
    args: dict[str, Any] = {"editor": editor or editor_options()}
    if data_url is not None:
        args["dataUrl"] = data_url
    if web_path is not None:
        args["webPath"] = web_path
    return call_bridge("editImage", args, callback=callback)


def setup_native_listeners(
    *,
    back_button: BackButtonMode = "emit",
    callback: Any = None,
) -> rx.event.EventSpec:
    """Register native → WebView listeners (app lifecycle, back button, keyboard).

    Call once on app load. Events are retrieved via :func:`poll_native_events`.

    ``back_button``:
      - ``emit`` — queue event for Reflex (default; blocks auto-exit on Android)
      - ``exit`` — quit the app immediately
      - ``history`` — ``window.history.back()`` when possible
    """
    return call_bridge(
        "setupNativeListeners",
        {"backButton": back_button},
        callback=callback,
    )


def poll_native_events(callback: Any) -> rx.event.EventSpec:
    """Drain queued native events since the last poll.

    Callback receives ``{events: [{ts, type, detail}, ...]}``.
    """
    return call_bridge("drainNativeEvents", callback=callback)


def push_register(*, callback: Any = None) -> rx.event.EventSpec:
    """Request push permission and register for FCM / APNs (requires push-notifications plugin).

    Registration token arrives as a ``pushRegistration`` native event via
    :func:`poll_native_events`.
    """
    return call_bridge("pushRegister", callback=callback)


def push_check_permissions(*, callback: Any = None) -> rx.event.EventSpec:
    """Check remote push notification permission status."""
    return call_bridge("pushCheckPermissions", callback=callback)


def push_request_permissions(*, callback: Any = None) -> rx.event.EventSpec:
    """Request remote push notification permission from the user."""
    return call_bridge("pushRequestPermissions", callback=callback)
