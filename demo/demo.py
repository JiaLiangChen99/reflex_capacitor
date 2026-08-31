"""Mobile-first demo app for reflex-capacitor (remote backend)."""

from __future__ import annotations

import json
import logging

import reflex as rx
from reflex_capacitor import CapacitorPlugin, get_upload_url, mobile
from reflex_capacitor.bridge import log_bridge

from demo.cloud_media import (
    AUDIO_NAME,
    VIDEO_NAME,
    demo_media_ready,
    ensure_demo_media,
    seed_demo_media_lifespan,
)

logging.getLogger("reflex_capacitor.bridge").setLevel(logging.DEBUG)

# --- visual tokens (mobile shell) ---
_BG = "#0f1419"
_SURFACE = "#1a222c"
_SURFACE_2 = "#243040"
_INK = "#e8eef4"
_MUTED = "#8b9aab"
_ACCENT = "#3d9a8b"
_ACCENT_DIM = "#2d7368"


def _upload_file_url(name: str) -> str:
    """Absolute backend URL for ``/_upload/<name>`` (Capacitor needs a full URL)."""
    return get_upload_url(name)


class State(rx.State):
    """App state: tab + counter round-trip to the remote Reflex backend."""

    tab: str = "home"
    count: int = 0
    bridge_msg: str = "点击下方按钮调用 Capacitor 原生能力（需在壳内运行）。"
    debug_diag: str = "进入本页或点「刷新诊断」查看 WebView / 插件状态。"
    debug_client_logs: str = "客户端日志：点原生按钮后点「刷新日志」。"
    native_events: str = "进入「原生」页后自动监听；点「刷新原生事件」查看。"
    last_deep_link: str = "（暂无 — 配置深链后用 adb / 链接打开 App，见 docs/deep-linking.md）"
    push_token: str = "（未注册 — 需 FCM/APNs，见 docs/push-notifications.md）"
    server_logs: list[str] = []
    cloud_media_status: str = "后端启动时会自动下载样例到 uploaded_files（/_upload）。"
    cloud_media_ready: bool = False

    def _append_server_log(self, line: str) -> None:
        self.server_logs = [line, *self.server_logs[:49]]

    def _sync_cloud_media_status(self) -> None:
        ready = demo_media_ready()
        self.cloud_media_ready = ready
        if ready:
            self.cloud_media_status = (
                f"已就绪\n音频: {_upload_file_url(AUDIO_NAME)}\n视频: {_upload_file_url(VIDEO_NAME)}"
            )
        else:
            self.cloud_media_status = (
                "样例尚未就绪（lifespan 仍在下载，或外网失败）。可点「重新拉取样例」。"
            )

    @rx.event
    def on_app_load(self):
        self._sync_cloud_media_status()
        return [
            mobile.setup_native_listeners(back_button="emit"),
            mobile.poll_native_events(State.on_native_events),
        ]

    @rx.event(background=True)
    async def reseed_cloud_media(self):
        """Manual re-download into ``uploaded_files`` (normally done by lifespan)."""
        import asyncio

        async with self:
            self.cloud_media_status = "正在重新下载样例到 uploaded_files/…"
            self._append_server_log(log_bridge("reseed_cloud_media", source="server"))
        info = await asyncio.to_thread(ensure_demo_media)
        async with self:
            self._sync_cloud_media_status()
            if not info.get("ok"):
                self.cloud_media_status = json.dumps(info, ensure_ascii=False, indent=2)
            self._append_server_log(
                log_bridge("reseed_cloud_media", result={"ok": info.get("ok")}, source="server")
            )

    @rx.event
    def play_cloud_audio(self):
        """Play backend ``/_upload/sample.mp3`` via bridge (simulates cloud audio URL)."""
        url = _upload_file_url(AUDIO_NAME)
        self.bridge_msg = f"播放云端音频: {url}"
        self._append_server_log(
            log_bridge("playRecording", args={"dataUrl": url}, source="server")
        )
        return mobile.play_recording(data_url=url, callback=State.on_bridge_result)

    @rx.event
    def set_tab(self, tab: str):
        self.tab = tab
        if tab == "native":
            self._sync_cloud_media_status()
            return [
                mobile.setup_native_listeners(back_button="emit"),
                mobile.diagnostics(State.on_diagnostics),
                mobile.bridge_logs(30, State.on_client_logs),
                mobile.poll_native_events(State.on_native_events),
            ]

    @rx.event
    def refresh_diagnostics(self):
        return mobile.diagnostics(State.on_diagnostics)

    @rx.event
    def refresh_client_logs(self):
        return mobile.bridge_logs(50, State.on_client_logs)

    @rx.event
    def clear_debug_logs(self):
        self.server_logs = []
        self.debug_client_logs = "（已清空）"
        self._append_server_log(log_bridge("clear_logs", source="server"))
        return mobile.clear_logs()

    @rx.event
    def on_diagnostics(self, result):
        if result is None:
            self.debug_diag = "无诊断数据（bridge 未加载？）"
            self._append_server_log(log_bridge("diagnostics", error="null", source="client"))
            return
        self.debug_diag = json.dumps(result, ensure_ascii=False, indent=2)
        self._append_server_log(log_bridge("diagnostics", result=result, source="client"))

    @rx.event
    def on_client_logs(self, result):
        if not result:
            self.debug_client_logs = "（暂无客户端日志）"
            return
        self.debug_client_logs = json.dumps(result, ensure_ascii=False, indent=2)
        self._append_server_log(
            log_bridge("bridge_logs", result={"count": len(result)}, source="client")
        )

    @rx.event
    def run_notify(self):
        self._append_server_log(
            log_bridge("notify", args={"title": "Shell"}, source="server")
        )
        return [
            mobile.notify("Shell", "来自 Reflex 的通知"),
            mobile.bridge_logs(30, State.on_client_logs),
        ]

    @rx.event
    def run_toast(self):
        self._append_server_log(log_bridge("toast", args={"text": "Hello Toast"}, source="server"))
        return [
            mobile.toast("Hello Toast"),
            mobile.bridge_logs(30, State.on_client_logs),
        ]

    @rx.event
    def run_haptics(self):
        self._append_server_log(log_bridge("hapticsImpact", args={"style": "HEAVY"}, source="server"))
        return mobile.haptics_impact(style="HEAVY", callback=State.on_bridge_result)

    @rx.event
    def run_haptics_vibrate(self):
        self._append_server_log(log_bridge("hapticsVibrate", args={"duration": 400}, source="server"))
        return mobile.haptics_vibrate(duration_ms=400, callback=State.on_bridge_result)

    @rx.event
    def run_share(self):
        self._append_server_log(log_bridge("share", source="server"))
        return [
            mobile.share(title="Shell", text="reflex-capacitor demo"),
            mobile.bridge_logs(30, State.on_client_logs),
        ]

    @rx.event
    def run_clipboard_write(self):
        self._append_server_log(log_bridge("clipboardWrite", source="server"))
        return [
            mobile.clipboard_write("reflex-capacitor clipboard"),
            mobile.bridge_logs(30, State.on_client_logs),
        ]

    @rx.event
    def run_clipboard_read(self):
        self._append_server_log(log_bridge("clipboardRead", source="server"))
        return mobile.clipboard_read(State.on_bridge_result)

    @rx.event
    def run_device_info(self):
        self._append_server_log(log_bridge("deviceInfo", source="server"))
        return mobile.device_info(State.on_bridge_result)

    @rx.event
    def run_network_status(self):
        self._append_server_log(log_bridge("networkStatus", source="server"))
        return mobile.network_status(State.on_bridge_result)

    @rx.event
    def run_pref_set(self):
        self._append_server_log(log_bridge("prefSet", args={"key": "shell_demo"}, source="server"))
        return mobile.pref_set("shell_demo", "hello-from-reflex", callback=State.on_bridge_result)

    @rx.event
    def run_pref_get(self):
        self._append_server_log(log_bridge("prefGet", source="server"))
        return mobile.pref_get("shell_demo", State.on_bridge_result)

    @rx.event
    def run_take_photo(self):
        self._append_server_log(log_bridge("takePhoto", source="server"))
        self.bridge_msg = "正在打开相机…"
        return mobile.take_photo(State.on_bridge_result, quality=80)

    @rx.event
    def run_pick_images(self):
        self._append_server_log(log_bridge("pickImages", source="server"))
        self.bridge_msg = "正在打开相册…"
        return mobile.pick_images(State.on_bridge_result, limit=3, quality=80)

    @rx.event
    def run_geolocation(self):
        self._append_server_log(log_bridge("getCurrentPosition", source="server"))
        self.bridge_msg = "正在定位（网络优先，约 15s）…"
        return [
            mobile.toast("正在定位…"),
            mobile.get_current_position(
                State.on_bridge_result,
                enable_high_accuracy=False,
                timeout_ms=30000,
            ),
        ]

    @rx.event
    def run_geolocation_gps(self):
        self._append_server_log(log_bridge("getCurrentPosition", args={"gps": True}, source="server"))
        self.bridge_msg = "正在 GPS 定位（可能需要 45s）…"
        return [
            mobile.toast("正在 GPS 定位…"),
            mobile.get_current_position(
                State.on_bridge_result,
                enable_high_accuracy=True,
                timeout_ms=45000,
            ),
        ]

    @rx.event
    def run_browser(self):
        self._append_server_log(log_bridge("browserOpen", source="server"))
        return mobile.browser_open("https://reflex.dev", callback=State.on_bridge_result)

    @rx.event
    def run_fs_write(self):
        self._append_server_log(log_bridge("fsWrite", source="server"))
        return mobile.fs_write(
            "demo-note.txt",
            "reflex-capacitor sandbox write",
            callback=State.on_bridge_result,
        )

    @rx.event
    def run_fs_read(self):
        self._append_server_log(log_bridge("fsRead", source="server"))
        return mobile.fs_read("demo-note.txt", State.on_bridge_result)

    @rx.event
    def run_start_recording(self):
        self._append_server_log(log_bridge("startRecording", source="server"))
        self.bridge_msg = "正在录音…"
        return [
            mobile.toast("开始录音"),
            mobile.start_recording(callback=State.on_bridge_result),
        ]

    @rx.event
    def run_stop_recording(self):
        self._append_server_log(log_bridge("stopRecording", source="server"))
        self.bridge_msg = "停止录音…"
        return mobile.stop_recording(State.on_bridge_result)

    @rx.event
    def run_play_recording(self):
        self._append_server_log(log_bridge("playRecording", source="server"))
        self.bridge_msg = "播放录音…"
        return mobile.play_recording(callback=State.on_bridge_result)

    @rx.event
    def run_stop_playback(self):
        self._append_server_log(log_bridge("stopPlayback", source="server"))
        return mobile.stop_playback(callback=State.on_bridge_result)

    @rx.event
    def run_recording_status(self):
        self._append_server_log(log_bridge("recordingStatus", source="server"))
        return mobile.recording_status(State.on_bridge_result)

    @rx.event
    def run_speak_demo(self):
        self._append_server_log(log_bridge("speak", source="server"))
        self.bridge_msg = "正在系统播报…"
        return mobile.speak(
            "你好，这是 python的reflex capacitor框架的系统语音播报示例。",
            lang="zh-CN",
            callback=State.on_bridge_result,
        )

    @rx.event
    def run_stop_speak(self):
        self._append_server_log(log_bridge("stopSpeak", source="server"))
        return mobile.stop_speak(callback=State.on_bridge_result)

    @rx.event
    def refresh_native_events(self):
        return mobile.poll_native_events(State.on_native_events)

    @rx.event
    def on_native_events(self, result):
        if not result or not isinstance(result, dict):
            self.native_events = "（暂无原生事件）"
            return
        events = result.get("events") or []
        if not events:
            self.native_events = "（队列为空 — 切后台/回前台、按返回键或注册推送试试）"
            return
        for ev in events:
            if not isinstance(ev, dict):
                continue
            ev_type = ev.get("type")
            detail = ev.get("detail") or {}
            if ev_type == "appUrlOpen":
                url = detail.get("url") or ""
                if url:
                    self.last_deep_link = url
            elif ev_type == "pushRegistration":
                token = detail.get("value") or ""
                if token:
                    preview = token if len(token) <= 48 else f"{token[:48]}…"
                    self.push_token = preview
            elif ev_type == "pushRegistrationError":
                self.push_token = f"注册失败: {detail.get('error', '?')}"
        self.native_events = json.dumps(events, ensure_ascii=False, indent=2)

    @rx.event
    def run_push_register(self):
        self._append_server_log(log_bridge("pushRegister", source="server"))
        return [
            mobile.push_register(callback=State.on_bridge_result),
            mobile.poll_native_events(State.on_native_events),
        ]

    @rx.event
    def run_keyboard_hide(self):
        self._append_server_log(log_bridge("keyboardHide", source="server"))
        return mobile.keyboard_hide(callback=State.on_bridge_result)

    @rx.event
    def increment(self):
        self.count += 1

    @rx.event
    def decrement(self):
        self.count -= 1

    @rx.event
    def reset_count(self):
        self.count = 0

    @rx.event
    def on_bridge_result(self, result):
        if result is None:
            self.bridge_msg = "无返回（可能不在 Capacitor 壳内，或 bridge 未加载）。"
            self._append_server_log(log_bridge("callback", error="null", source="client"))
        elif isinstance(result, dict):
            if result.get("cancelled"):
                self.bridge_msg = "已取消操作。"
                self._append_server_log(log_bridge("callback", result={"cancelled": True}, source="client"))
                return mobile.bridge_logs(30, State.on_client_logs)
            preview = dict(result)
            data_url = preview.get("dataUrl")
            if isinstance(data_url, str) and len(data_url) > 96:
                preview["dataUrl"] = f"{data_url[:96]}… ({len(data_url)} chars)"
            photos = preview.get("photos")
            if isinstance(photos, list):
                preview["photos"] = [
                    {**p, "webPath": (p.get("webPath") or "")[:64] + "…" if len(p.get("webPath") or "") > 64 else p.get("webPath")}
                    if isinstance(p, dict)
                    else p
                    for p in photos
                ]
            self.bridge_msg = json.dumps(preview, ensure_ascii=False, indent=2)
            self._append_server_log(log_bridge("callback", result=preview, source="client"))
        else:
            self.bridge_msg = str(result)
            self._append_server_log(log_bridge("callback", result=result, source="client"))
        return mobile.bridge_logs(30, State.on_client_logs)


def _top_bar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text("SHELL", size="1", weight="bold", letter_spacing="0.12em", color=_ACCENT),
                rx.heading("今日", size="5", weight="bold", color=_INK),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            rx.badge("在线", variant="soft", color_scheme="teal", size="2"),
            width="100%",
            align="center",
        ),
        padding_x="4",
        padding_top="calc(0.75rem + env(safe-area-inset-top, 0px))",
        padding_bottom="3",
        background=_BG,
        border_bottom=f"1px solid {_SURFACE_2}",
        width="100%",
    )


def _nav_item(label: str, icon: str, tab: str) -> rx.Component:
    active = State.tab == tab
    return rx.button(
        rx.vstack(
            rx.icon(icon, size=22),
            rx.text(label, size="1", weight="medium"),
            spacing="1",
            align="center",
        ),
        on_click=State.set_tab(tab),
        variant="ghost",
        color=rx.cond(active, _ACCENT, _MUTED),
        height="auto",
        padding_y="2",
        flex="1",
        style={"_hover": {"background": "transparent", "color": _ACCENT}},
    )


def _bottom_nav() -> rx.Component:
    return rx.box(
        rx.hstack(
            _nav_item("首页", "house", "home"),
            _nav_item("计数", "gauge", "counter"),
            _nav_item("原生", "smartphone", "native"),
            _nav_item("我的", "user", "me"),
            width="100%",
            justify="between",
            align="center",
        ),
        padding_x="2",
        padding_top="2",
        padding_bottom="calc(0.5rem + env(safe-area-inset-bottom, 0px))",
        background=_SURFACE,
        border_top=f"1px solid {_SURFACE_2}",
        width="100%",
    )


def _home_panel() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.text("远程后端", size="2", color=_MUTED),
                rx.heading("状态在云端", size="6", color=_INK),
                rx.text(
                    "界面跑在 Capacitor 壳里，点击会打到你配置的 Reflex 后端。",
                    size="2",
                    color=_MUTED,
                ),
                spacing="2",
                align="start",
            ),
            padding="5",
            border_radius="1.25rem",
            background=(
                f"linear-gradient(145deg, {_SURFACE_2} 0%, {_SURFACE} 55%, {_ACCENT_DIM} 160%)"
            ),
            width="100%",
        ),
        rx.button(
            "去计数页试试",
            on_click=State.set_tab("counter"),
            size="3",
            width="100%",
            style={
                "background": _ACCENT,
                "color": "#04120f",
                "font_weight": "600",
            },
        ),
        spacing="4",
        width="100%",
    )


def _counter_panel() -> rx.Component:
    return rx.vstack(
        rx.text("当前计数", size="2", color=_MUTED),
        rx.heading(State.count, size="9", weight="bold", color=_INK),
        rx.hstack(
            rx.button(
                rx.icon("minus", size=22),
                on_click=State.decrement,
                size="4",
                flex="1",
                height="3.5rem",
                style={"background": _SURFACE_2, "color": _INK},
            ),
            rx.button(
                rx.icon("plus", size=22),
                on_click=State.increment,
                size="4",
                flex="1",
                height="3.5rem",
                style={"background": _ACCENT, "color": "#04120f"},
            ),
            width="100%",
            spacing="3",
        ),
        rx.button(
            "清零",
            on_click=State.reset_count,
            variant="ghost",
            color_scheme="gray",
            size="2",
        ),
        spacing="4",
        align="center",
        width="100%",
        padding_y="4",
    )


def _native_btn(label: str, icon: str, handler) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label, size="2"),
            spacing="2",
            align="center",
        ),
        on_click=handler,
        size="3",
        width="100%",
        style={"background": _SURFACE_2, "color": _INK, "justify_content": "flex-start"},
    )


def _debug_block(title: str, content) -> rx.Component:
    return rx.box(
        rx.text(title, size="2", weight="bold", color=_MUTED, margin_bottom="2"),
        rx.box(
            rx.text(
                content,
                size="1",
                color=_INK,
                white_space="pre-wrap",
                word_break="break-word",
                font_family="monospace",
            ),
            max_height="10rem",
            overflow_y="auto",
            width="100%",
        ),
        padding="3",
        border_radius="0.75rem",
        background=_SURFACE,
        width="100%",
    )


def _native_panel() -> rx.Component:
    return rx.vstack(
        rx.text("Phase 2–5 · 原生桥 + 深链/推送", size="2", color=_MUTED),
        rx.text(
            "P0 基础能力 + P1 + 反向事件（返回键 / 前后台 / 键盘）+ Phase 5 深链与推送。"
            "真机开发可试 reflex-capacitor dev android。",
            size="2",
            color=_MUTED,
        ),
        rx.hstack(
            rx.button(
                "刷新诊断",
                on_click=State.refresh_diagnostics,
                size="2",
                flex="1",
                style={"background": _SURFACE_2, "color": _INK},
            ),
            rx.button(
                "刷新日志",
                on_click=State.refresh_client_logs,
                size="2",
                flex="1",
                style={"background": _SURFACE_2, "color": _INK},
            ),
            rx.button(
                "刷新原生事件",
                on_click=State.refresh_native_events,
                size="2",
                flex="1",
                style={"background": _SURFACE_2, "color": _INK},
            ),
            rx.button(
                "清空",
                on_click=State.clear_debug_logs,
                size="2",
                variant="ghost",
                color_scheme="gray",
            ),
            width="100%",
            spacing="2",
        ),
        _debug_block("诊断 (WebView)", State.debug_diag),
        _debug_block("最近深链 (appUrlOpen)", State.last_deep_link),
        _debug_block("推送 token (pushRegistration)", State.push_token),
        _debug_block("原生事件 (反向)", State.native_events),
        _debug_block("客户端日志 (bridge.js)", State.debug_client_logs),
        _debug_block("服务端日志 (回调到后端)", State.server_logs.join("\n")),
        rx.separator(size="4", color_scheme="gray"),
        _native_btn("本地通知", "bell", State.run_notify),
        _native_btn("Toast", "message-square", State.run_toast),
        _native_btn("轻触反馈 (HEAVY)", "vibrate", State.run_haptics),
        _native_btn("长震动 400ms", "smartphone", State.run_haptics_vibrate),
        _native_btn("分享", "share-2", State.run_share),
        _native_btn("写入剪贴板", "clipboard-copy", State.run_clipboard_write),
        _native_btn("读取剪贴板", "clipboard", State.run_clipboard_read),
        _native_btn("设备信息", "cpu", State.run_device_info),
        _native_btn("网络状态", "wifi", State.run_network_status),
        rx.separator(size="4", color_scheme="gray"),
        rx.text("Phase 3 · P1", size="2", weight="bold", color=_ACCENT),
        _native_btn("写入偏好 shell_demo", "bookmark", State.run_pref_set),
        _native_btn("读取偏好 shell_demo", "bookmark-check", State.run_pref_get),
        _native_btn("拍照 (dataUrl)", "camera", State.run_take_photo),
        _native_btn("相册选图", "images", State.run_pick_images),
        _native_btn("当前定位 (网络)", "map-pin", State.run_geolocation),
        _native_btn("高精度 GPS", "navigation", State.run_geolocation_gps),
        _native_btn("打开 reflex.dev", "globe", State.run_browser),
        _native_btn("沙箱写文件", "file-plus", State.run_fs_write),
        _native_btn("沙箱读文件", "file-text", State.run_fs_read),
        _native_btn("隐藏键盘", "keyboard", State.run_keyboard_hide),
        rx.separator(size="4", color_scheme="gray"),
        rx.text("云端媒体（模拟）", size="2", weight="bold", color=_ACCENT),
        rx.text(
            "后端 lifespan 下载到 uploaded_files；前端用 reflex_capacitor.get_upload_url。",
            size="1",
            color=_MUTED,
        ),
        _native_btn("重新拉取样例", "cloud-download", State.reseed_cloud_media),
        _native_btn("播放云端 MP3", "music", State.play_cloud_audio),
        _native_btn("停止播放", "square", State.run_stop_playback),
        _debug_block("云端媒体状态", State.cloud_media_status),
        rx.cond(
            State.cloud_media_ready,
            rx.vstack(
                rx.text("云端视频预览 (Cap get_upload_url)", size="1", color=_MUTED),
                rx.el.video(
                    src=get_upload_url(VIDEO_NAME),
                    controls=True,
                    plays_inline=True,
                    style={
                        "width": "100%",
                        "maxHeight": "220px",
                        "borderRadius": "12px",
                        "background": "#000",
                    },
                ),
                rx.el.audio(
                    src=get_upload_url(AUDIO_NAME),
                    controls=True,
                    style={"width": "100%"},
                ),
                width="100%",
                spacing="2",
            ),
            rx.fragment(),
        ),
        rx.separator(size="4", color_scheme="gray"),
        rx.text("录音 / 回放", size="2", weight="bold", color=_ACCENT),
        _native_btn("开始录音", "mic", State.run_start_recording),
        _native_btn("停止录音", "mic-off", State.run_stop_recording),
        _native_btn("播放刚录的音频", "play", State.run_play_recording),
        _native_btn("停止播放", "square", State.run_stop_playback),
        _native_btn("录音状态", "activity", State.run_recording_status),
        rx.separator(size="4", color_scheme="gray"),
        rx.text("系统播报 (TTS)", size="2", weight="bold", color=_ACCENT),
        _native_btn("播报固定话", "volume-2", State.run_speak_demo),
        _native_btn("停止播报", "volume-x", State.run_stop_speak),
        rx.separator(size="4", color_scheme="gray"),
        rx.text("Phase 5 · 深链 / 推送", size="2", weight="bold", color=_ACCENT),
        _native_btn("注册远程推送", "radio", State.run_push_register),
        _debug_block("最近一次回调结果", State.bridge_msg),
        spacing="3",
        width="100%",
        padding_y="2",
    )


def _me_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.avatar(fallback="S", size="4", color_scheme="teal"),
            rx.vstack(
                rx.text("Shell 用户", weight="bold", color=_INK),
                rx.text("Phase 3 · remote + P0/P1 bridge", size="2", color=_MUTED),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        rx.separator(size="4", color_scheme="gray"),
        rx.vstack(
            rx.text("说明", size="2", weight="bold", color=_MUTED),
            rx.text(
                "本页只是壳内演示。后端地址由构建时烘焙"
                "（本机 rxconfig 或 CI 的 Environment Secret REFLEX_BACKEND_URL）。",
                size="2",
                color=_MUTED,
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        spacing="5",
        width="100%",
        padding_y="2",
    )


def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            _top_bar(),
            rx.box(
                rx.cond(
                    State.tab == "home",
                    _home_panel(),
                    rx.cond(
                        State.tab == "counter",
                        _counter_panel(),
                        rx.cond(
                            State.tab == "native",
                            _native_panel(),
                            _me_panel(),
                        ),
                    ),
                ),
                flex="1",
                width="100%",
                padding_x="4",
                padding_y="4",
                overflow_y="auto",
            ),
            _bottom_nav(),
            spacing="0",
            width="100%",
            max_width="28rem",
            min_height="100dvh",
            margin_x="auto",
            background=_BG,
        ),
        width="100%",
        min_height="100dvh",
        background=_BG,
    )


app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="teal",
        gray_color="slate",
        radius="large",
        scaling="100%",
    ),
)
app.register_lifespan_task(seed_demo_media_lifespan)
app.add_page(index, route="/", title="Shell", on_load=State.on_app_load)
