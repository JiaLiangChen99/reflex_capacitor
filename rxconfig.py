import reflex as rx

from reflex_capacitor import CapacitorPlugin

config = rx.Config(
    app_name="demo",
    # Capacitor WebView is cross-origin vs your API — allow Cap origins (or "*").
    cors_allowed_origins=["*"],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(),
        CapacitorPlugin(
            # Local sync/run only. CI ignores this and uses Environment secret
            # REFLEX_BACKEND_URL (see docs/ci.md).
            # Examples for local device testing:
            #   backend_url="http://192.168.1.56:8001",
            #   backend_url="http://10.0.2.2:8000",  # Android emulator → host
            backend_url=None,
            app_name="Shell",
            app_id="dev.reflex.capacitor.demo",
        ),
    ],
)
