# Package a Reflex app as a Capacitor mobile app (remote backend).

Ship the same Reflex frontend you already have into an iOS / Android WebView via
[Capacitor](https://capacitorjs.com), talking to a **hosted** Reflex backend over HTTPS/WSS.

```bash
pip install -e .          # or: uv sync && uv pip install -e .
reflex-capacitor doctor
reflex-capacitor init     # scaffold capacitor/ + add android
# set CapacitorPlugin(backend_url="https://your-api…") in rxconfig.py
reflex-capacitor run android
```

Phase 1 scope: **shell + remote backend** only (no in-app Python, no native bridge yet).
Design notes live under [`docs/`](docs/).

## Wire it up

```python
# rxconfig.py
import reflex as rx
from reflex_capacitor import CapacitorPlugin

config = rx.Config(
    app_name="demo",
    cors_allowed_origins=["*"],  # or capacitor://localhost, http://localhost
    plugins=[
        CapacitorPlugin(
            backend_url="https://api.example.com",
            app_id="com.example.myapp",
            app_name="My App",
        ),
    ],
)
```

## Commands

```bash
reflex-capacitor doctor              # Node / npm (+ optional Android / iOS flags)
reflex-capacitor init                # scaffold capacitor/, npm i, cap add android
reflex-capacitor sync                # reflex export → www/ → npx cap sync
reflex-capacitor run android         # sync + launch emulator/device
reflex-capacitor open android        # Android Studio
```

On Windows, **Android** is the practical target; iOS needs macOS.

## Layout

| Path | Role |
|------|------|
| `src/reflex_capacitor/` | Installable library (`CapacitorPlugin`, CLI) |
| `demo/` | Sample Reflex app in this repo |
| `capacitor/` | Generated Capacitor project (after `init` / `sync`) |

## Backend URL tips

- Production: HTTPS API + WSS event endpoint (baked into `env.json` at export time).
- Emulator → host machine: often `http://10.0.2.2:8000` (Android emulator loopback to host).
- Physical device: use your PC's LAN IP and open the firewall for the backend port.
- CI: set `REFLEX_CAPACITOR_DEV_BACKEND_URL` or the workflow input — see [`docs/ci.md`](docs/ci.md).

## CI (no Android Studio on your PC)

GitHub Actions [`.github/workflows/android-apk.yml`](.github/workflows/android-apk.yml)
builds a **debug APK**. Backend URL is read from **Environment secret**
`REFLEX_BACKEND_URL` (environments: `lan` / `staging` / `production`).

1. Create Environments + secret (see [`docs/ci.md`](docs/ci.md))
2. Actions → **Android APK** → Run workflow → pick environment
3. Download artifact `app-debug-<env>` and install on a phone
