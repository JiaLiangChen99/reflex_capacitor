"""``reflex-capacitor`` CLI — export Reflex frontend into a Capacitor shell."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import click

from . import preflight
from .android_signing import (
    AndroidSigningConfig,
    apply_release_signing,
    release_output_paths,
)
from .config import DEFAULT_CAPACITOR_DIR, DEV_BACKEND_URL_ENV
from .dev_util import guess_lan_ip, wait_for_http_ok, wait_for_port
from .network_env import PROXY_ENV_VAR, child_env, gradle_jvm_proxy_args, normalize_proxy_url

# Active --proxy for this CLI invocation (None = no proxy; ambient proxy env stripped).
_active_proxy: str | None = None

F = TypeVar("F", bound=Callable[..., Any])


def _proxy_option(f: F) -> F:
    """Shared ``--proxy`` flag (default: off; also reads ``REFLEX_CAPACITOR_PROXY``)."""
    return click.option(
        "--proxy",
        default=None,
        envvar=PROXY_ENV_VAR,
        help=(
            "HTTP(S) proxy for npm / Gradle downloads only "
            f"(env: {PROXY_ENV_VAR}). Default: no proxy "
            "(ignores ambient http_proxy / HTTPS_PROXY)."
        ),
    )(f)


def _activate_proxy(proxy: str | None) -> None:
    """Validate and store proxy for subsequent ``_run`` / Gradle calls."""
    global _active_proxy
    if not proxy:
        _active_proxy = None
        return
    try:
        _active_proxy = normalize_proxy_url(proxy)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"reflex-capacitor: using proxy {_active_proxy}")


def _find_plugin(app_root: Path):
    """Find the ``CapacitorPlugin`` configured in ``rxconfig.py``."""
    try:
        from reflex_base.config import get_config

        from .plugin import CapacitorPlugin

        for plugin in get_config().plugins:
            if isinstance(plugin, CapacitorPlugin):
                return plugin
    except Exception as exc:  # noqa: BLE001
        click.echo(f"reflex-capacitor: could not read rxconfig ({exc})", err=True)
    return None


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run a subprocess, echoing the command; abort on failure."""
    merged = child_env(proxy=_active_proxy)
    if env:
        merged.update(env)
    click.echo(f"reflex-capacitor: $ {' '.join(cmd)}  (in {cwd})")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=False, env=merged)
    except FileNotFoundError as exc:
        raise click.ClickException(f"command not found: {cmd[0]} ({exc})") from exc
    if result.returncode != 0:
        raise click.ClickException(f"{cmd[0]} exited with code {result.returncode}")


def _reflex_cmd() -> list[str]:
    """Resolve the ``reflex`` executable from the same venv when possible."""
    sibling = Path(sys.executable).parent / ("reflex.exe" if os.name == "nt" else "reflex")
    reflex_bin = str(sibling) if sibling.exists() else shutil.which("reflex")
    return [reflex_bin] if reflex_bin else [sys.executable, "-m", "reflex"]


def _npm_cmd() -> str:
    """Return npm executable name for the current platform."""
    return "npm.cmd" if os.name == "nt" else "npm"


def _npx_cmd() -> list[str]:
    """Return npx invocation (Windows uses npx.cmd)."""
    if os.name == "nt":
        return ["npx.cmd"]
    return ["npx"]


def _preflight(
    *,
    need_android: bool = False,
    need_ios: bool = False,
    need_device: bool = False,
) -> None:
    """Fail fast when required host tooling is missing (never auto-installs)."""
    checks = preflight.run_checks(
        need_android=need_android,
        need_ios=need_ios,
        need_device=need_device,
    )
    missing = preflight.failed_required(checks)
    if not missing:
        return
    raise click.ClickException(preflight.format_missing_report(missing))


def _print_doctor_report(checks: list[preflight.Check]) -> None:
    """Pretty-print check results and a missing summary."""
    click.echo("reflex-capacitor doctor — host dependency check")
    click.echo(
        "(reports only; does not install Node / JDK / Android SDK / Xcode)\n"
    )
    for check in checks:
        mark = click.style("ok", fg="green") if check.ok else click.style("MISSING", fg="red")
        optional = "" if check.required else click.style(" (optional)", fg="yellow")
        click.echo(f"  [{mark}] {check.name}{optional}: {check.detail}")
        if not check.ok and check.remediation:
            click.echo("\n".join(f"         {line}" for line in check.remediation.splitlines()))

    missing = preflight.failed_required(checks)
    warnings = preflight.failed_optional(checks)
    if missing:
        click.echo(click.style("\nRequired — still missing:", fg="red", bold=True))
        for check in missing:
            click.echo(f"  • {check.name}: {check.detail}")
    if warnings:
        click.echo(click.style("\nOptional — missing (non-blocking):", fg="yellow"))
        for check in warnings:
            click.echo(f"  • {check.name}: {check.detail}")
    if not missing:
        click.echo(click.style("\nAll required checks passed.", fg="green"))
    else:
        click.echo(
            "\nInstall the missing tools yourself, then re-run "
            "`reflex-capacitor doctor` / `check`."
        )


def _capacitor_root(app_root: Path, plugin) -> Path:
    """Resolve the Capacitor project directory."""
    name = plugin.capacitor_dir if plugin else DEFAULT_CAPACITOR_DIR
    return (app_root / name).resolve()


def _ensure_plugin(app_root: Path):
    """Require a CapacitorPlugin in rxconfig."""
    plugin = _find_plugin(app_root)
    if plugin is None:
        raise click.ClickException(
            "no CapacitorPlugin in rxconfig.py — add:\n\n"
            "  from reflex_capacitor import CapacitorPlugin\n\n"
            "  config = rx.Config(\n"
            "      ...,\n"
            '      cors_allowed_origins=["*"],\n'
            "      plugins=[..., CapacitorPlugin(backend_url=\"https://your-api.example\")],\n"
            "  )\n"
        )
    return plugin


def _reflex_export(app_root: Path) -> None:
    """Build the static frontend (fires CapacitorPlugin.post_build)."""
    _run([*_reflex_cmd(), "export", "--frontend-only"], cwd=app_root)


def _npm_install(cap_root: Path) -> None:
    """Install Capacitor npm dependencies."""
    _run([_npm_cmd(), "install"], cwd=cap_root)


def _finalize_bridge(plugin, cap_root: Path) -> None:
    """Copy vendor plugin JS into www after npm install (when export has run)."""
    bridge_js = cap_root / plugin.web_dir / "assets" / "reflex-capacitor" / "bridge.js"
    if bridge_js.is_file():
        plugin.finalize_bridge(cap_root)

def _cap_sync(cap_root: Path) -> None:
    """Copy web assets into native projects."""
    _run([*_npx_cmd(), "cap", "sync"], cwd=cap_root)


def _ensure_platform(cap_root: Path, platform: str) -> None:
    """Add ios/android platform if the native project folder is missing."""
    native_dir = cap_root / platform
    if native_dir.is_dir():
        return
    click.echo(f"reflex-capacitor: adding Capacitor platform {platform!r}…")
    _run([*_npx_cmd(), "cap", "add", platform], cwd=cap_root)


@click.group()
def main() -> None:
    """Package a Reflex app as a Capacitor mobile app (remote backend)."""


@main.command("doctor")
@click.option("--android", "need_android", is_flag=True, help="Also check Android SDK + JDK.")
@click.option("--ios", "need_ios", is_flag=True, help="Also check iOS / Xcode tooling.")
@click.option(
    "--device",
    "need_device",
    is_flag=True,
    help="Also require adb (for run/dev on a phone/emulator).",
)
def doctor(need_android: bool, need_ios: bool, need_device: bool) -> None:
    """Check host dependencies (Reflex / Node / JDK / SDK). Does not install them."""
    if need_device and not need_android:
        need_android = True
    checks = preflight.run_checks(
        need_android=need_android,
        need_ios=need_ios,
        need_device=need_device,
    )
    _print_doctor_report(checks)
    click.echo(
        "\nTip: set CapacitorPlugin(backend_url=...) to your hosted API "
        "(HTTPS + WSS in production)."
    )
    if preflight.failed_required(checks):
        n = len(preflight.failed_required(checks))
        raise click.ClickException(f"{n} required check(s) failed.")


@main.command("check")
@click.option("--android", "need_android", is_flag=True, help="Also check Android SDK + JDK.")
@click.option("--ios", "need_ios", is_flag=True, help="Also check iOS / Xcode tooling.")
@click.option(
    "--device",
    "need_device",
    is_flag=True,
    help="Also require adb (for run/dev on a phone/emulator).",
)
@click.pass_context
def check_cmd(
    ctx: click.Context,
    need_android: bool,
    need_ios: bool,
    need_device: bool,
) -> None:
    """Alias for ``doctor`` — verify host dependencies before packaging."""
    ctx.invoke(
        doctor,
        need_android=need_android,
        need_ios=need_ios,
        need_device=need_device,
    )

@main.command("init")
@click.option(
    "--app-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
    help="App root containing rxconfig.py.",
)
@click.option(
    "--platform",
    "platforms",
    multiple=True,
    type=click.Choice(["android", "ios"]),
    default=("android",),
    help="Native platform(s) to add (default: android). Repeatable.",
)
@_proxy_option
def init_cmd(app_dir: str, platforms: tuple[str, ...], proxy: str | None) -> None:
    """Scaffold the Capacitor project and add native platforms."""
    _activate_proxy(proxy)
    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    _preflight(need_android="android" in platforms, need_ios="ios" in platforms)
    plugin = _ensure_plugin(app_root)
    cap_root = _capacitor_root(app_root, plugin)

    # Trigger scaffold via a lightweight export, or scaffold directly if www empty.
    if not (cap_root / ".reflex-capacitor").exists():
        plugin._scaffold(cap_root)
        plugin._configure(cap_root)
        click.echo(f"reflex-capacitor: scaffolded {cap_root}")
    else:
        plugin._configure(cap_root)
        click.echo(f"reflex-capacitor: Capacitor project already exists at {cap_root}")

    _npm_install(cap_root)
    _finalize_bridge(plugin, cap_root)
    for platform in platforms:
        if platform == "ios" and sys.platform != "darwin":
            click.echo(
                click.style(
                    "reflex-capacitor: skipping ios (requires macOS).",
                    fg="yellow",
                )
            )
            continue
        _ensure_platform(cap_root, platform)

    click.echo(
        click.style("\nDone.", fg="green")
        + " Next: set backend_url in CapacitorPlugin, then run:\n"
        "  reflex-capacitor sync\n"
        "  reflex-capacitor run android"
    )


@main.command()
@click.option(
    "--app-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
)
@click.option("--skip-export", is_flag=True, help="Reuse existing www/ without re-exporting.")
@click.option(
    "--platform",
    "platforms",
    multiple=True,
    type=click.Choice(["android", "ios"]),
    default=(),
    help="Ensure these platforms exist before sync (optional).",
)
@_proxy_option
def sync(app_dir: str, skip_export: bool, platforms: tuple[str, ...], proxy: str | None) -> None:
    """Export the Reflex frontend and ``npx cap sync``."""
    _activate_proxy(proxy)
    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    _preflight()
    plugin = _ensure_plugin(app_root)
    cap_root = _capacitor_root(app_root, plugin)

    if not skip_export:
        _reflex_export(app_root)
    elif not (cap_root / plugin.web_dir).is_dir():
        raise click.ClickException(
            f"no {plugin.web_dir}/ under {cap_root} — run without --skip-export first"
        )

    if not (cap_root / "package.json").exists():
        raise click.ClickException(
            f"Capacitor project missing at {cap_root} — run `reflex-capacitor init` first"
        )

    _npm_install(cap_root)
    _finalize_bridge(plugin, cap_root)
    for platform in platforms:
        if platform == "ios" and sys.platform != "darwin":
            continue
        _ensure_platform(cap_root, platform)

    # If a platform was added earlier, sync it; if none yet, still sync core.
    _cap_sync(cap_root)
    # Safety net: Android blocks http:// API calls unless cleartext is on.
    plugin.ensure_android_cleartext(cap_root)

    if plugin.backend_url:
        click.echo(f"reflex-capacitor: remote backend → {plugin.backend_url}")
    elif os.environ.get(DEV_BACKEND_URL_ENV):
        click.echo(
            f"reflex-capacitor: using {DEV_BACKEND_URL_ENV}="
            f"{os.environ[DEV_BACKEND_URL_ENV]}"
        )
    else:
        click.echo(
            click.style(
                "reflex-capacitor: warning — no backend_url set; frontend uses config.api_url.",
                fg="yellow",
            )
        )
    click.echo(click.style("sync complete.", fg="green"))


@main.command()
@click.argument("platform", type=click.Choice(["android", "ios"]))
@click.option(
    "--app-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
)
@click.option("--skip-sync", is_flag=True, help="Skip export + cap sync; just run.")
@click.option(
    "--target",
    default=None,
    help="Optional device / emulator id passed to `npx cap run`.",
)
@_proxy_option
def run(
    platform: str,
    app_dir: str,
    skip_sync: bool,
    target: str | None,
    proxy: str | None,
) -> None:
    """Sync (unless skipped) and launch on a device / emulator."""
    if platform == "ios" and sys.platform != "darwin":
        raise click.ClickException("iOS requires macOS + Xcode.")

    _activate_proxy(proxy)
    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    _preflight(
        need_android=platform == "android",
        need_ios=platform == "ios",
        need_device=platform == "android",
    )
    plugin = _ensure_plugin(app_root)
    cap_root = _capacitor_root(app_root, plugin)

    if not skip_sync:
        # Inline sync so one command gets you onto a device.
        ctx = click.get_current_context()
        ctx.invoke(
            sync,
            app_dir=app_dir,
            skip_export=False,
            platforms=(platform,),
            proxy=proxy,
        )
    else:
        _ensure_platform(cap_root, platform)

    cmd = [*_npx_cmd(), "cap", "run", platform]
    if target:
        cmd.extend(["--target", target])
    _run(cmd, cwd=cap_root)


def _android_dir(cap_root: Path) -> Path:
    android = cap_root / "android"
    if not android.is_dir():
        raise click.ClickException(
            f"Android project missing at {android} — run `reflex-capacitor init --platform android`"
        )
    return android


def _gradle_build(android_root: Path, task: str) -> None:
    gradlew = android_root / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if not gradlew.is_file():
        raise click.ClickException(f"Gradle wrapper missing at {gradlew}")
    if os.name != "nt":
        gradlew.chmod(gradlew.stat().st_mode | 0o111)
    cmd = [str(gradlew), task, "--no-daemon", "--stacktrace"]
    if _active_proxy:
        # Command-line -D overrides stale systemProp.* in gradle.properties.
        cmd[1:1] = gradle_jvm_proxy_args(_active_proxy)
    _run(cmd, cwd=android_root)


def _resolve_android_signing(
    keystore_path: str | None,
    keystore_password: str | None,
    key_alias: str | None,
    key_password: str | None,
) -> AndroidSigningConfig | None:
    """Resolve signing from CLI flags or environment."""
    if keystore_path:
        if not (keystore_password and key_alias and key_password):
            raise click.ClickException(
                "with --keystore-path also pass --keystore-password, --key-alias, --key-password "
                "(or set REFLEX_CAPACITOR_KEYSTORE_* env vars)"
            )
        return AndroidSigningConfig(
            keystore_path=Path(keystore_path),
            keystore_password=keystore_password,
            key_alias=key_alias,
            key_password=key_password,
        )
    try:
        return AndroidSigningConfig.from_env()
    except (ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc


@main.command()
@click.argument("platform", type=click.Choice(["android", "ios"]))
@click.option(
    "--app-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
)
@click.option(
    "--release/--debug",
    default=True,
    help="Release (signed when keystore env is set) or debug build.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["apk", "aab"]),
    default="apk",
    help="Android output type (release only; AAB for Play Store).",
)
@click.option("--skip-sync", is_flag=True, help="Skip export + cap sync before building.")
@click.option(
    "--keystore-path",
    default=None,
    envvar="REFLEX_CAPACITOR_KEYSTORE_PATH",
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    help="Android release keystore (.jks / .keystore).",
)
@click.option(
    "--keystore-password",
    default=None,
    envvar="REFLEX_CAPACITOR_KEYSTORE_PASSWORD",
    help="Keystore password.",
)
@click.option(
    "--key-alias",
    default=None,
    envvar="REFLEX_CAPACITOR_KEY_ALIAS",
    help="Key alias inside the keystore.",
)
@click.option(
    "--key-password",
    default=None,
    envvar="REFLEX_CAPACITOR_KEY_PASSWORD",
    help="Key password.",
)
@_proxy_option
def build(
    platform: str,
    app_dir: str,
    release: bool,
    output_format: str,
    skip_sync: bool,
    keystore_path: str | None,
    keystore_password: str | None,
    key_alias: str | None,
    key_password: str | None,
    proxy: str | None,
) -> None:
    """Build a release/debug APK/AAB (Android) or archive (iOS, macOS only)."""
    if platform == "ios" and sys.platform != "darwin":
        raise click.ClickException("iOS build requires macOS + Xcode.")

    _activate_proxy(proxy)
    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    _preflight(need_android=platform == "android", need_ios=platform == "ios")
    plugin = _ensure_plugin(app_root)
    cap_root = _capacitor_root(app_root, plugin)

    if not skip_sync:
        ctx = click.get_current_context()
        ctx.invoke(
            sync,
            app_dir=app_dir,
            skip_export=False,
            platforms=(platform,),
            proxy=proxy,
        )
    else:
        _ensure_platform(cap_root, platform)

    if platform == "android":
        android_root = _android_dir(cap_root)
        if release:
            signing = _resolve_android_signing(
                keystore_path,
                keystore_password,
                key_alias,
                key_password,
            )
            if signing:
                apply_release_signing(android_root, signing)
                click.echo(f"reflex-capacitor: release signing configured ({signing.key_alias})")
            else:
                click.echo(
                    click.style(
                        "reflex-capacitor: no keystore — release build may fail. "
                        "Set REFLEX_CAPACITOR_KEYSTORE_* or see docs/publishing.md.",
                        fg="yellow",
                    )
                )
            task = "bundleRelease" if output_format == "aab" else "assembleRelease"
        else:
            task = "assembleDebug"
        click.echo(f"reflex-capacitor: ./gradlew {task}")
        _gradle_build(android_root, task)
        artifacts = release_output_paths(android_root, aab=release and output_format == "aab")
        if not artifacts and not release:
            artifacts = sorted((android_root / "app" / "build" / "outputs" / "apk" / "debug").glob("*.apk"))
        if artifacts:
            click.echo(click.style("Build output:", fg="green"))
            for path in artifacts:
                click.echo(f"  {path}")
        else:
            click.echo(
                click.style(
                    "Build finished — check android/app/build/outputs/ for artifacts.",
                    fg="green",
                )
            )
        return

    cap_cmd = [*_npx_cmd(), "cap", "build", "ios"]
    if release:
        cap_cmd.extend(["--xcode-export-method", "release-testing"])
    click.echo(f"reflex-capacitor: {' '.join(cap_cmd)}")
    _run(cap_cmd, cwd=cap_root)


def _default_dev_ports() -> tuple[int, int]:
    """Return Reflex default frontend/backend dev ports."""
    try:
        from reflex_base.constants import DefaultPorts

        return int(DefaultPorts.FRONTEND_PORT), int(DefaultPorts.BACKEND_PORT)
    except (ImportError, AttributeError, TypeError, ValueError):
        return 3000, 8000


def _backend_health_url(backend_port: int) -> str:
    """Build the Reflex backend health check URL on loopback."""
    try:
        from reflex_base.config import get_config

        config = get_config()
        prepend = getattr(config, "prepend_backend_path", None)
        path = prepend("/_health") if callable(prepend) else "/_health"
    except Exception:  # noqa: BLE001
        path = "/_health"
    return f"http://127.0.0.1:{backend_port}{path}"


@main.command()
@click.argument("platform", type=click.Choice(["android", "ios"]))
@click.option(
    "--app-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
)
@click.option(
    "--lan-ip",
    default=None,
    help="Dev machine LAN IP for the phone (default: auto-detect).",
)
@click.option("--frontend-port", default=None, type=int, help="Reflex dev frontend port.")
@click.option("--backend-port", default=None, type=int, help="Reflex dev backend port.")
@click.option(
    "--live-reload/--no-live-reload",
    default=False,
    help="Load UI from the dev frontend (server.url) instead of bundled www/.",
)
@click.option("--skip-export", is_flag=True, help="Reuse existing www/ (still runs cap sync).")
@click.option(
    "--target",
    default=None,
    help="Optional device / emulator id passed to `npx cap run`.",
)
@_proxy_option
def dev(
    platform: str,
    app_dir: str,
    lan_ip: str | None,
    frontend_port: int | None,
    backend_port: int | None,
    live_reload: bool,
    skip_export: bool,
    target: str | None,
    proxy: str | None,
) -> None:
    """Develop on a device: export, sync, start Reflex dev server, launch the app.

    Default mode (``--no-live-reload``): bundles the static frontend into the APK shell
    and runs only the Reflex **backend** on your LAN IP — same as CI + ``reflex run
    --backend-only``, but automated.

    With ``--live-reload``: points Capacitor ``server.url`` at the Vite dev server for
    hot reload (phone and PC must be on the same Wi‑Fi; firewall must allow the ports).
    """
    if platform == "ios" and sys.platform != "darwin":
        raise click.ClickException("iOS dev requires macOS + Xcode.")

    _activate_proxy(proxy)
    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    _preflight(
        need_android=platform == "android",
        need_ios=platform == "ios",
        need_device=platform == "android",
    )
    plugin = _ensure_plugin(app_root)
    cap_root = _capacitor_root(app_root, plugin)

    if not (cap_root / "package.json").exists():
        raise click.ClickException(
            f"Capacitor project missing at {cap_root} — run `reflex-capacitor init` first"
        )

    default_fe, default_be = _default_dev_ports()
    fe_port = frontend_port or default_fe
    be_port = backend_port or default_be
    host_ip = (lan_ip or guess_lan_ip()).strip()
    backend_url = f"http://{host_ip}:{be_port}"
    frontend_url = f"http://{host_ip}:{fe_port}"

    click.echo(f"reflex-capacitor dev — LAN backend → {backend_url}")
    if live_reload:
        click.echo(f"reflex-capacitor dev — live UI     → {frontend_url}")
    else:
        click.echo("reflex-capacitor dev — UI from bundled www/ (re-export on each dev start)")

    dev_env = {**os.environ, DEV_BACKEND_URL_ENV: backend_url}

    if not skip_export:
        click.echo("reflex-capacitor: exporting frontend with dev backend URL…")
        _run([*_reflex_cmd(), "export", "--frontend-only"], cwd=app_root, env=dev_env)
    elif not (cap_root / plugin.web_dir).is_dir():
        raise click.ClickException(
            f"no {plugin.web_dir}/ under {cap_root} — run without --skip-export first"
        )

    _npm_install(cap_root)
    _finalize_bridge(plugin, cap_root)
    _ensure_platform(cap_root, platform)

    if live_reload:
        plugin.apply_dev_server(cap_root, frontend_url=frontend_url)
    else:
        plugin.clear_dev_server(cap_root)

    _cap_sync(cap_root)
    plugin.ensure_android_cleartext(cap_root)

    reflex_cmd = [*_reflex_cmd(), "run", "--backend-host", "0.0.0.0", "--backend-port", str(be_port)]
    if live_reload:
        reflex_cmd.extend(["--frontend-port", str(fe_port)])
    else:
        reflex_cmd.append("--backend-only")

    click.echo(f"reflex-capacitor: starting `{' '.join(reflex_cmd[1:])}` …")
    reflex_proc = subprocess.Popen(reflex_cmd, cwd=app_root, env=dev_env)
    try:
        if live_reload:
            wait_for_port(fe_port, reflex_proc)
        wait_for_port(be_port, reflex_proc)
        wait_for_http_ok(_backend_health_url(be_port), reflex_proc)
        click.echo(click.style("reflex dev server is up.", fg="green"))

        cap_cmd = [*_npx_cmd(), "cap", "run", platform]
        if target:
            cap_cmd.extend(["--target", target])
        _run(cap_cmd, cwd=cap_root)
    except (RuntimeError, click.ClickException) as exc:
        raise click.ClickException(str(exc)) from exc
    finally:
        if reflex_proc.poll() is None:
            reflex_proc.terminate()
            try:
                reflex_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                reflex_proc.kill()
        if live_reload:
            plugin.clear_dev_server(cap_root)
            click.echo("reflex-capacitor: cleared Capacitor server.url (run sync before release builds)")


@main.command("open")
@click.argument("platform", type=click.Choice(["android", "ios"]))
@click.option(
    "--app-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
)
def open_cmd(platform: str, app_dir: str) -> None:
    """Open the native project in Android Studio / Xcode."""
    if platform == "ios" and sys.platform != "darwin":
        raise click.ClickException("iOS requires macOS + Xcode.")

    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    plugin = _ensure_plugin(app_root)
    cap_root = _capacitor_root(app_root, plugin)
    if not (cap_root / platform).is_dir():
        raise click.ClickException(
            f"platform {platform!r} not found — run `reflex-capacitor init --platform {platform}`"
        )
    _run([*_npx_cmd(), "cap", "open", platform], cwd=cap_root)
