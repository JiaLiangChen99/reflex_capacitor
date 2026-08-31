import reflex as rx

from reflex_capacitor import CapacitorPlugin
from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS, PHASE5_PLUGIN_IDS

config = rx.Config(
    app_name="demo",
    # Capacitor WebView is cross-origin vs your API — allow Cap origins (or "*").
    cors_allowed_origins=["*"],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(),
        CapacitorPlugin(
            # Hardcoded LAN backend for device testing (no trailing slash).
            # Android needs Capacitor server.cleartext=true for http:// — the plugin
            # flips that automatically when backend_url starts with http://.
            backend_url="http://192.168.1.56:8003",  # 真机调试改为你 PC 的局域网 IP
            app_name="Shell",
            app_id="dev.reflex.capacitor.demo",
            # Default is already ALL_PLUGIN_IDS; demo also enables remote push.
            plugins=ALL_PLUGIN_IDS + PHASE5_PLUGIN_IDS,
        ),
    ],
)
