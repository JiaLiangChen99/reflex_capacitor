"""Mobile-first demo app for reflex-capacitor (remote backend)."""

from __future__ import annotations

import reflex as rx

# --- visual tokens (mobile shell) ---
_BG = "#0f1419"
_SURFACE = "#1a222c"
_SURFACE_2 = "#243040"
_INK = "#e8eef4"
_MUTED = "#8b9aab"
_ACCENT = "#3d9a8b"
_ACCENT_DIM = "#2d7368"


class State(rx.State):
    """App state: tab + counter round-trip to the remote Reflex backend."""

    tab: str = "home"
    count: int = 0

    @rx.event
    def set_tab(self, tab: str):
        self.tab = tab

    @rx.event
    def increment(self):
        self.count += 1

    @rx.event
    def decrement(self):
        self.count -= 1

    @rx.event
    def reset_count(self):
        self.count = 0


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


def _me_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.avatar(fallback="S", size="4", color_scheme="teal"),
            rx.vstack(
                rx.text("Shell 用户", weight="bold", color=_INK),
                rx.text("Phase 1 · remote backend", size="2", color=_MUTED),
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
                        _me_panel(),
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
app.add_page(index, route="/", title="Shell")
