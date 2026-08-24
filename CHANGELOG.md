# Changelog

All notable changes to this project are documented here.

## [0.2.0] — 2026-08-24

Phase 1–4 core complete. See [docs/00-getting-started.md](docs/00-getting-started.md) for the full workflow.

### Phase 4 — Release builds

- `reflex-capacitor build android|ios` — release/debug APK/AAB via Gradle
- Android signing via `REFLEX_CAPACITOR_KEYSTORE_*` env vars or CLI flags
- [docs/publishing.md](docs/publishing.md) — keystore, Play Store, iOS notes
- GitHub Actions workflow `android-release-aab.yml` (manual, production secrets)

### Phase 3 — P1 + dev experience

- P1 bridge APIs: camera, geolocation, preferences, filesystem, keyboard, browser, `invoke`
- Built-in image editor (free crop, pinch zoom) — [docs/image-editor.md](docs/image-editor.md)
- `reflex-capacitor dev android` — LAN device development — [docs/dev-reload.md](docs/dev-reload.md)
- Native reverse events: `setup_native_listeners`, `poll_native_events`
- Camera/geolocation Android fixes (permissions, feedback toasts)

### Phase 2 — Native bridge P0

- `window.__REFLEX_CAPACITOR__` + `mobile.*` Python API
- P0: notify, toast, haptics, share, clipboard, device, network, etc.
- Demo native tab + CI Environment matrix (lan / staging / production)
- [docs/permissions.md](docs/permissions.md), [docs/debug.md](docs/debug.md)

### Phase 1 — Shell + remote backend

- `CapacitorPlugin`, CLI (`init`, `sync`, `run`, `open`, `doctor`)
- HTTP LAN backend support (`cleartext`, `androidScheme: http`)
- GitHub Actions debug APK — [docs/ci.md](docs/ci.md)

## [0.1.0] — Initial

- Project scaffold, remote Capacitor shell concept
