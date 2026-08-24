# Package a Reflex app as a Capacitor mobile app (remote backend).

Ship the same Reflex frontend you already have into an iOS / Android WebView via
[Capacitor](https://capacitorjs.com), talking to a **hosted** Reflex backend over HTTPS/WSS.

```bash
pip install -e .
reflex-capacitor doctor
reflex-capacitor init --platform android
# configure CapacitorPlugin(backend_url=...) in rxconfig.py
reflex-capacitor sync
reflex-capacitor run android          # debug on device/emulator
reflex-capacitor build android        # release APK/AAB
```

Design notes: [`docs/`](docs/) · **Start here:** [`docs/00-getting-started.md`](docs/00-getting-started.md) · [CHANGELOG.md](CHANGELOG.md)

## Wire it up

```python
# rxconfig.py
import reflex as rx
from reflex_capacitor import CapacitorPlugin
from reflex_capacitor.bridge.plugins import ALL_PLUGIN_IDS

config = rx.Config(
    app_name="demo",
    cors_allowed_origins=["*"],  # production: restrict to your API + Capacitor origins
    plugins=[
        CapacitorPlugin(
            backend_url="https://api.example.com",
            app_id="com.example.myapp",
            app_name="My App",
            plugins=ALL_PLUGIN_IDS,
        ),
    ],
)
```

## Commands

| Command | Purpose |
|---------|---------|
| `reflex-capacitor doctor` | Check Node / npm / optional Android SDK |
| `reflex-capacitor init` | Scaffold `capacitor/`, `npm install`, `cap add` |
| `reflex-capacitor sync` | `reflex export` → `www/` → `npx cap sync` |
| `reflex-capacitor run android\|ios` | Sync + launch on device/emulator |
| `reflex-capacitor dev android` | LAN dev: export + backend on `0.0.0.0` + run ([dev-reload.md](docs/dev-reload.md)) |
| `reflex-capacitor build android\|ios` | Release/debug APK, AAB, or iOS archive ([publishing.md](docs/publishing.md)) |
| `reflex-capacitor open android\|ios` | Open Android Studio / Xcode |

On Windows, **Android** is the practical target; iOS needs macOS.

## Python API (`mobile.*`)

```python
from reflex_capacitor import mobile

# P0 — notify, toast, share, clipboard, device, …
mobile.notify("Hello", "From Reflex")

# P1 — camera, geolocation, preferences, filesystem, …
mobile.get_current_position(State.on_gps)

# Phase 3 — native → Reflex events
mobile.setup_native_listeners(back_button="emit")
mobile.poll_native_events(State.on_native_events)
```

Full API: [`docs/02-native-bridge.md`](docs/02-native-bridge.md)

## Layout

| Path | Role |
|------|------|
| `src/reflex_capacitor/` | Library (`CapacitorPlugin`, CLI, bridge) |
| `demo/` | Sample Reflex app |
| `capacitor/` | Generated Capacitor project (after `init`) |

## Backend URL

| Environment | URL | Notes |
|-------------|-----|-------|
| Production | `https://…` | WSS event; required for store builds |
| LAN dev | `http://192.168.x.x:8001` | Needs cleartext + `androidScheme: http` (auto) |
| Emulator → host | `http://10.0.2.2:8000` | Android emulator loopback |

## CI

- **Debug APK** — push/PR builds `lan`; manual matrix for staging/production ([ci.md](docs/ci.md))
- **Release AAB** — manual workflow + production signing secrets ([publishing.md](docs/publishing.md))

## Limitations

- **Remote backend only** — no embedded Python on device
- **Not a mobile UI kit** — use Reflex components + `mobile.*` bridge
- Push notifications / biometrics — Phase 4+ optional ([roadmap](docs/04-roadmap.md))
