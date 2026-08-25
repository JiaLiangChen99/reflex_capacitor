#!/usr/bin/env bash
# L3 device smoke — install debug APK, launch, check bridge logcat, optional deep link.
#
# Prerequisites:
#   - adb on PATH, exactly one device (or set ADB_SERIAL)
#   - debug APK built (or leave SKIP_BUILD=0 to sync + assembleDebug)
#
# Usage:
#   ./scripts/device-smoke.sh
#   SKIP_BUILD=1 ./scripts/device-smoke.sh
#   ADB_SERIAL=XXXX REQUIRE_DEEP_LINK=1 ./scripts/device-smoke.sh
#
# See docs/design/testing.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LAUNCH_WAIT_SEC="${LAUNCH_WAIT_SEC:-5}"
DEEP_LINK_SCHEME="${DEEP_LINK_SCHEME:-shell}"
DEEP_LINK_HOST="${DEEP_LINK_HOST:-open}"
SKIP_BUILD="${SKIP_BUILD:-0}"
SKIP_DEEP_LINK="${SKIP_DEEP_LINK:-0}"
REQUIRE_DEEP_LINK="${REQUIRE_DEEP_LINK:-0}"
FORCE_BUILD="${FORCE_BUILD:-0}"

APK="${APK:-$ROOT/capacitor/android/app/build/outputs/apk/debug/app-debug.apk}"

adb_cmd() {
  if [[ -n "${ADB_SERIAL:-}" ]]; then
    adb -s "$ADB_SERIAL" "$@"
  else
    adb "$@"
  fi
}

die() {
  echo "device-smoke: ERROR: $*" >&2
  exit 1
}

info() {
  echo "device-smoke: $*"
}

require_adb() {
  command -v adb >/dev/null 2>&1 || die "adb not found on PATH"
}

require_device() {
  require_adb
  local count
  if [[ -n "${ADB_SERIAL:-}" ]]; then
    adb_cmd get-state >/dev/null 2>&1 || die "device $ADB_SERIAL not reachable"
    info "using device $ADB_SERIAL"
    return
  fi
  count="$(adb devices | awk 'NR>1 && $2=="device"{print $1}' | wc -l | tr -d ' ')"
  if [[ "$count" -eq 0 ]]; then
    die "no adb device — connect phone (USB debugging) or start emulator"
  fi
  if [[ "$count" -gt 1 ]]; then
    die "multiple adb devices — set ADB_SERIAL to one serial (adb devices)"
  fi
  ADB_SERIAL="$(adb devices | awk 'NR>1 && $2=="device"{print $1; exit}')"
  info "using device $ADB_SERIAL"
}

resolve_app_id() {
  if [[ -n "${APP_ID:-}" ]]; then
    return
  fi
  local conf="$ROOT/capacitor/capacitor.config.json"
  [[ -f "$conf" ]] || die "APP_ID unset and missing $conf — run reflex-capacitor init/sync first"
  APP_ID="$(python3 -c "import json; print(json.load(open('$conf'))['appId'])")"
  [[ -n "$APP_ID" ]] || die "appId missing in $conf"
}

maybe_build() {
  if [[ "$SKIP_BUILD" == "1" ]]; then
    [[ -f "$APK" ]] || die "SKIP_BUILD=1 but APK missing at $APK — build first"
    info "using existing APK $APK"
    return
  fi
  if [[ -f "$APK" && "$FORCE_BUILD" != "1" ]]; then
    info "using existing APK $APK (set FORCE_BUILD=1 to rebuild)"
    return
  fi
  info "building debug APK (reflex-capacitor sync + gradlew assembleDebug)…"
  if command -v uv >/dev/null 2>&1; then
    uv run reflex-capacitor sync
  else
    reflex-capacitor sync
  fi
  [[ -d "$ROOT/capacitor/android" ]] || die "capacitor/android missing after sync"
  (cd "$ROOT/capacitor/android" && chmod +x gradlew && ./gradlew assembleDebug --no-daemon --stacktrace)
  [[ -f "$APK" ]] || die "APK not found after build: $APK"
}

install_and_launch() {
  info "installing $APK"
  adb_cmd install -r "$APK" >/dev/null

  info "clearing logcat and launching ${APP_ID}/.MainActivity"
  adb_cmd logcat -c || true
  adb_cmd shell am start -W -n "${APP_ID}/.MainActivity" >/dev/null
  sleep "$LAUNCH_WAIT_SEC"
}

check_bridge_logs() {
  local logs
  logs="$(adb_cmd logcat -d 2>/dev/null || true)"
  if echo "$logs" | grep -q '\[reflex-capacitor\]'; then
    info "bridge logcat OK (found [reflex-capacitor])"
    echo "$logs" | grep '\[reflex-capacitor\]' | tail -n 5 || true
    return 0
  fi
  if echo "$logs" | grep -qi 'reflex-capacitor'; then
    info "bridge logcat OK (found reflex-capacitor)"
    return 0
  fi
  die "bridge not seen in logcat — check sync/inject or open app in Capacitor shell"
}

check_deep_link() {
  if [[ "$SKIP_DEEP_LINK" == "1" ]]; then
    info "skipping deep link (SKIP_DEEP_LINK=1)"
    return 0
  fi
  local url="${DEEP_LINK_SCHEME}://${DEEP_LINK_HOST}/home?from=device-smoke"
  info "firing deep link: $url"
  adb_cmd logcat -c || true
  adb_cmd shell am start -W -a android.intent.action.VIEW -d "$url" "$APP_ID" >/dev/null 2>&1 || true
  sleep 3
  local logs
  logs="$(adb_cmd logcat -d 2>/dev/null || true)"
  if echo "$logs" | grep -qE 'appUrlOpen|nativeEvent.*appUrlOpen'; then
    info "deep link OK (appUrlOpen in logcat)"
    return 0
  fi
  local msg="deep link not observed — add intent-filter (see docs/deep-linking.md) or set SKIP_DEEP_LINK=1"
  if [[ "$REQUIRE_DEEP_LINK" == "1" ]]; then
    die "$msg"
  fi
  info "WARN: $msg"
}

main() {
  require_device
  resolve_app_id
  info "appId=$APP_ID"
  maybe_build
  install_and_launch
  check_bridge_logs
  check_deep_link
  info "smoke passed"
}

main "$@"
