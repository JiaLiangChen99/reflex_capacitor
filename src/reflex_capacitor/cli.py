"""``reflex-capacitor`` CLI — export Reflex frontend into a Capacitor shell."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click

from . import preflight
from .config import DEFAULT_CAPACITOR_DIR, DEV_BACKEND_URL_ENV


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
    click.echo(f"reflex-capacitor: $ {' '.join(cmd)}  (in {cwd})")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=False, env=env)
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


def _preflight(*, need_android: bool = False, need_ios: bool = False) -> None:
    """Fail fast when required Node tooling is missing."""
    missing = preflight.failed_required(
        preflight.run_checks(need_android=need_android, need_ios=need_ios)
    )
    if not missing:
        return
    lines = ["missing build prerequisites — install the following, then re-run:\n"]
    for check in missing:
        lines.append(f"  ✗ {check.name}: {check.detail}")
        lines += [f"      {line}" for line in check.remediation.splitlines()]
        lines.append("")
    lines.append("Run `reflex-capacitor doctor` to recheck.")
    raise click.ClickException("\n".join(lines))


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


@main.command()
@click.option("--android", "need_android", is_flag=True, help="Also check Android tooling.")
@click.option("--ios", "need_ios", is_flag=True, help="Also check iOS / Xcode tooling.")
def doctor(need_android: bool, need_ios: bool) -> None:
    """Check Node / npm / optional native SDKs."""
    checks = preflight.run_checks(need_android=need_android, need_ios=need_ios)
    click.echo("reflex-capacitor doctor — mobile build prerequisites\n")
    for check in checks:
        mark = click.style("ok", fg="green") if check.ok else click.style("MISSING", fg="red")
        optional = "" if check.required else click.style(" (optional)", fg="yellow")
        click.echo(f"  [{mark}] {check.name}{optional}: {check.detail}")
        if not check.ok and check.remediation:
            click.echo("\n".join(f"         {line}" for line in check.remediation.splitlines()))
    click.echo(
        "\nPhase 1 uses a *remote* Reflex backend — set CapacitorPlugin(backend_url=...) "
        "to your hosted API (HTTPS + WSS in production)."
    )
    missing = preflight.failed_required(checks)
    if missing:
        raise click.ClickException(
            f"{len(missing)} required check(s) failed — install the above, then re-run."
        )
    click.echo(click.style("\nAll required checks passed.", fg="green"))


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
def init_cmd(app_dir: str, platforms: tuple[str, ...]) -> None:
    """Scaffold the Capacitor project and add native platforms."""
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
def sync(app_dir: str, skip_export: bool, platforms: tuple[str, ...]) -> None:
    """Export the Reflex frontend and ``npx cap sync``."""
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
def run(platform: str, app_dir: str, skip_sync: bool, target: str | None) -> None:
    """Sync (unless skipped) and launch on a device / emulator."""
    if platform == "ios" and sys.platform != "darwin":
        raise click.ClickException("iOS requires macOS + Xcode.")

    app_root = Path(app_dir).resolve()
    os.chdir(app_root)
    _preflight(need_android=platform == "android", need_ios=platform == "ios")
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
        )
    else:
        _ensure_platform(cap_root, platform)

    cmd = [*_npx_cmd(), "cap", "run", platform]
    if target:
        cmd.extend(["--target", target])
    _run(cmd, cwd=cap_root)


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
