# Package a Reflex app as a Capacitor mobile app

Ship the same Reflex frontend into an iOS / Android WebView via
[Capacitor](https://capacitorjs.com), talking to a **hosted** Reflex backend over HTTPS/WSS.

**Docs (Chinese howto / design / roadmap):** [`docs/README.md`](docs/README.md) ·
**Start here:** [`docs/guide/00-getting-started.md`](docs/guide/00-getting-started.md) ·
[FAQ](docs/guide/faq.md) · [Install & PyPI](docs/guide/install.md) · [CHANGELOG](CHANGELOG.md)

```bash
pip install reflex-capacitor   # or: pip install -e .
reflex-capacitor check --android
reflex-capacitor init --platform android
# set CapacitorPlugin(backend_url=...) in rxconfig.py
reflex-capacitor sync
reflex-capacitor run android           # device / emulator
reflex-capacitor build android --debug # APK
```

Host toolchains (Node / JDK / Android SDK / Xcode) are **detected, never auto-installed**.
See [`docs/guide/cli.md`](docs/guide/cli.md) and [`docs/guide/install.md`](docs/guide/install.md).

## Configure

```python
# rxconfig.py
import reflex as rx
from reflex_capacitor import CapacitorPlugin

config = rx.Config(
    app_name="demo",
    cors_allowed_origins=["*"],  # tighten in production
    plugins=[
        CapacitorPlugin(
            backend_url="https://api.example.com",
            app_id="com.example.myapp",
            app_name="My App",
            # plugins defaults to ALL_PLUGIN_IDS (camera/TTS/recorder/…; no push)
        ),
    ],
)
```

Push notifications are **opt-in** (`PHASE5_PLUGIN_IDS`). Details:
[`docs/guide/configuration.md`](docs/guide/configuration.md),
[`docs/guide/push-notifications.md`](docs/guide/push-notifications.md).

## Commands

| Command | Purpose |
|---------|---------|
| `doctor` / `check` | Host dependency report (`--android`, `--device`, `--ios`) |
| `init` | Scaffold `capacitor/`, `npm install`, `cap add` |
| `sync` | `reflex export` → `www/` → `npx cap sync` |
| `run` / `dev` | Sync + launch (dev: LAN backend helper) |
| `build` | Release/debug APK, AAB, or iOS archive |
| `open` | Open Android Studio / Xcode |

Proxy for npm/Gradle (off by default): `--proxy URL` or `REFLEX_CAPACITOR_PROXY`.

Full CLI: [`docs/guide/cli.md`](docs/guide/cli.md) · Dev reload: [`docs/guide/dev-reload.md`](docs/guide/dev-reload.md) ·
Store signing: [`docs/guide/publishing.md`](docs/guide/publishing.md)

## Python API

```python
from reflex_capacitor import mobile

mobile.notify("Hello", "From Reflex")
mobile.get_current_position(State.on_gps)
mobile.setup_native_listeners(back_button="emit")
mobile.poll_native_events(State.on_native_events)
```

API map: [`docs/guide/02-native-bridge.md`](docs/guide/02-native-bridge.md)

## Backend URL

| Environment | URL | Notes |
|-------------|-----|-------|
| Production | `https://…` | WSS; required for store builds |
| LAN | `http://192.168.x.x:port` | cleartext + `androidScheme: http` (automatic) |
| Emulator → host | `http://10.0.2.2:8000` | Android emulator loopback |

Network & CORS: [`docs/guide/configuration.md`](docs/guide/configuration.md)

## Layout

| Path | Role |
|------|------|
| `src/reflex_capacitor/` | Library (`CapacitorPlugin`, CLI, bridge) |
| `demo/` | Sample app |
| `capacitor/` | Generated Capacitor project (after `init`) |
| `docs/` | Docs hub: [`docs/README.md`](docs/README.md) (`guide/` + `design/`) |

## CI

- Debug APK — [`docs/guide/ci.md`](docs/guide/ci.md)
- Release AAB — [`docs/guide/publishing.md`](docs/guide/publishing.md)

## Limitations

- **Remote backend only** — no embedded Python on device
- **Not a mobile UI kit** — Reflex UI + `mobile.*` bridge
- **Android-first** — iOS needs macOS; no iOS CI in this repo yet
- Host SDKs checked by `check`, never installed by this tool
