# Changelog

## Unreleased

### Phase 4 — Release builds

- `reflex-capacitor build android|ios` — release/debug APK/AAB via Gradle
- Android signing via `REFLEX_CAPACITOR_KEYSTORE_*` env vars or CLI flags
- `docs/publishing.md` — keystore, Play Store, iOS notes
- Optional GitHub Actions workflow for signed production AAB

### Phase 3 — P1 + dev experience

- P1 bridge APIs: camera, geolocation, preferences, filesystem, keyboard, browser, `invoke`
- Built-in image editor (free crop, pinch zoom)
- `reflex-capacitor dev android` — LAN device development
- Native reverse events: `setup_native_listeners`, `poll_native_events`
- `docs/dev-reload.md`

### Phase 2 — Native bridge P0

- `window.__REFLEX_CAPACITOR__` + `mobile.*` Python API
- P0: notify, toast, haptics, share, clipboard, device, network, etc.
- Demo native tab + CI Environment matrix (lan / staging / production)
- `docs/permissions.md`, `docs/debug.md`

### Phase 1 — Shell + remote backend

- `CapacitorPlugin`, CLI (`init`, `sync`, `run`, `open`, `doctor`)
- HTTP LAN backend support (`cleartext`, `androidScheme: http`)
- GitHub Actions debug APK
