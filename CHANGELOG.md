# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Features

- Built-in voice recording / playback in packaged ``bridge.js`` (``mobile.start_recording`` / ``stop_recording`` / ``play_recording``); enable ``voice-recorder`` for mic permissions
- ``CapacitorPlugin`` loads bridge scripts during ``reflex run`` (browser) via Vite ``public/`` + document inject

### Fixes

- Proxy unit test expected wrong Gradle port (``7892`` typo vs ``7890``)

## [0.3.2] — 2026-08-25

### Fixes

- `project.urls` must be absolute HTTPS links for PyPI (relative `docs/README.md` caused upload 400)

## [0.3.1] — 2026-08-25

### Fixes

- Hatch wheel: drop redundant `force-include` for `bridge/assets` (already packaged via `packages`), which caused duplicate `bridge.js` and failed `python -m build`

## [0.3.0] — 2026-08-25

Phase 5 features for PyPI, plus a Python 3.12 compatibility fix for Android manifest permission patching.

### Fixes

- Android `uses-permission` insert: use positional `str.replace(..., 1)` (Python 3.12 rejects `count=` keyword)

### Deep linking

- [docs/guide/deep-linking.md](docs/guide/deep-linking.md) — Android / iOS URL scheme 配置与 Reflex 事件处理
- Demo：`appUrlOpen` 展示、`on_app_load` 自动轮询原生事件

### Push notifications

- `PHASE5_PLUGIN_IDS` — optional `push-notifications` plugin tier
- `mobile.push_register()` / `push_check_permissions()` / `push_request_permissions()`
- Bridge push listeners → `pushRegistration`, `pushNotificationReceived`, etc.
- [docs/guide/push-notifications.md](docs/guide/push-notifications.md) — FCM / APNs 接入说明
- Documented as **opt-in** for PyPI consumers (not in default `ALL_PLUGIN_IDS`)

### CLI proxy (npm / Gradle)

- `--proxy URL` on `init` / `sync` / `run` / `build` / `dev` (env: `REFLEX_CAPACITOR_PROXY`)
- Default: **no proxy**; ambient `http_proxy` / `HTTPS_PROXY` are stripped for child processes

### Host dependency checks

- Stronger `doctor` / alias `check`: Reflex, Node, npm, JDK 17+, Android SDK platforms & build-tools
- `init` / `build` / `run` / `dev` fail fast with an explicit missing list (no auto-install of host SDKs)
- `--device` requires `adb` for run/dev

### PyPI publish CI

- [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml) — on GitHub Release `published`; secret `PYPI_API_TOKEN`
- Verifies wheel includes `bridge.js` + scaffold; tag `vX.Y.Z` must match `pyproject.toml` version

### Docs restructure (2026-08-25)

- [docs/README.md](docs/README.md) — hub; docs split into **`guide/`** (howto) + **`design/`** (architecture & plan)
- New howto: [cli](docs/guide/cli.md), [configuration](docs/guide/configuration.md), [android-build](docs/guide/android-build.md), [install](docs/guide/install.md), [faq](docs/guide/faq.md)
- New design: [packaging](docs/design/packaging.md), [security-network](docs/design/security-network.md)
- Slim [getting-started](docs/guide/00-getting-started.md); [roadmap](docs/design/04-roadmap.md); [ADR](docs/design/03-development-plan.md)
- Docs split: `guide/` (user) + `design/` (maintainer); merged plan/ADR; PyPI sdist ships core guide only

### L1 integration tests

- `tests/test_integration_scaffold.py` — offline scaffold / post_build / finalize_bridge / Manifest
- `tests/conftest.py` — fixtures
- `tests/helpers.py` — fake export / node_modules helpers
- Run: `pytest tests/ -m integration`

### L3 device smoke

- `scripts/device-smoke.sh` — adb install, launch, logcat bridge check, optional deep link
- `tests/test_device_smoke.py` — `-m device` (skips without adb)
- [docs/guide/testing.md](docs/guide/testing.md)

### iOS platform compatibility

- `bridge/ios_plist.py` — Info.plist usage descriptions on `finalize_bridge`
- `mobile.platform_info()` + bridge `isAndroid` / `isIos` / `platformInfo`
- [docs/guide/platform.md](docs/guide/platform.md)

## [0.2.0] — 2026-08-24

Phase 1–4 core complete. See [docs/guide/00-getting-started.md](docs/guide/00-getting-started.md) for the full workflow.

### Phase 4 — Release builds

- `reflex-capacitor build android|ios` — release/debug APK/AAB via Gradle
- Android signing via `REFLEX_CAPACITOR_KEYSTORE_*` env vars or CLI flags
- [docs/guide/publishing.md](docs/guide/publishing.md) — keystore, Play Store, iOS notes
- GitHub Actions workflow `android-release-aab.yml` (manual, production secrets)

### Phase 3 — P1 + dev experience

- P1 bridge APIs: camera, geolocation, preferences, filesystem, keyboard, browser, `invoke`
- Built-in image editor (free crop, pinch zoom) — [docs/guide/image-editor.md](docs/guide/image-editor.md)
- `reflex-capacitor dev android` — LAN device development — [docs/guide/dev-reload.md](docs/guide/dev-reload.md)
- Native reverse events: `setup_native_listeners`, `poll_native_events`
- Camera/geolocation Android fixes (permissions, feedback toasts)

### Phase 2 — Native bridge P0

- `window.__REFLEX_CAPACITOR__` + `mobile.*` Python API
- P0: notify, toast, haptics, share, clipboard, device, network, etc.
- Demo native tab + CI Environment matrix (lan / staging / production)
- [docs/guide/permissions.md](docs/guide/permissions.md), [docs/guide/debug.md](docs/guide/debug.md)

### Phase 1 — Shell + remote backend

- `CapacitorPlugin`, CLI (`init`, `sync`, `run`, `open`, `doctor`)
- HTTP LAN backend support (`cleartext`, `androidScheme: http`)
- GitHub Actions debug APK — [docs/guide/ci.md](docs/guide/ci.md)

## [0.1.0] — Initial

- Project scaffold, remote Capacitor shell concept
