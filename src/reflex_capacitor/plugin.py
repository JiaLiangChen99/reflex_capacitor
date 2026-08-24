"""Reflex plugin that wires a Reflex build into a Capacitor mobile shell (remote backend)."""

from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
from pathlib import Path

from reflex.plugins import Plugin

from .config import (
    CAPACITOR_ORIGINS,
    CAPACITOR_VERSION,
    DEFAULT_CAPACITOR_DIR,
    DEFAULT_WEB_DIR,
    DEV_BACKEND_URL_ENV,
    default_app_id,
    slugify,
)

# Marker so we know this directory was scaffolded by reflex-capacitor.
_SCAFFOLD_MARKER = ".reflex-capacitor"


@dataclasses.dataclass(kw_only=True, frozen=True)
class CapacitorPlugin(Plugin):
    """Package the compiled Reflex frontend into a Capacitor app (remote backend only).

    Bakes the backend URL into ``env.json`` at compile time, scaffolds a Capacitor
    project under ``capacitor_dir``, and copies the static frontend into ``webDir``.

    Attributes:
        backend_url: Base URL of the hosted Reflex backend. When ``None``, leaves
            ``config.api_url`` unchanged (unless ``REFLEX_CAPACITOR_DEV_BACKEND_URL`` is set).
        app_name: Display name. Defaults to the Reflex app name.
        app_id: Reverse-DNS bundle id (e.g. ``com.example.myapp``).
        capacitor_dir: Capacitor project directory relative to the app root.
        web_dir: Folder name inside ``capacitor_dir`` used as Capacitor ``webDir``.
    """

    backend_url: str | None = None
    app_name: str | None = None
    app_id: str | None = None
    capacitor_dir: str = DEFAULT_CAPACITOR_DIR
    web_dir: str = DEFAULT_WEB_DIR

    def _resolved_names(self) -> tuple[str, str]:
        """Resolve display name and app id from config defaults.

        Returns:
            ``(app_name, app_id)``.
        """
        from reflex_base.config import get_config

        reflex_name = get_config().app_name
        name = self.app_name or reflex_name or "Reflex App"
        app_id = self.app_id or default_app_id(reflex_name or "app")
        return name, app_id

    def _backend_base(self) -> str | None:
        """Return the backend base URL to bake into ``env.json``."""
        if dev_backend_url := os.environ.get(DEV_BACKEND_URL_ENV):
            return dev_backend_url.rstrip("/")
        if self.backend_url:
            return self.backend_url.rstrip("/")
        return None

    def update_env_json(self, **context) -> dict[str, str] | None:
        """Rebuild baked backend endpoint URLs against the chosen backend base.

        Args:
            context: Unused plugin context.

        Returns:
            Endpoint name → URL mapping, or ``None`` to leave defaults.
        """
        from reflex_base.config import get_config
        from reflex_base.constants.event import Endpoint

        base = self._backend_base()
        if base is None:
            return None

        config = get_config()
        prepend = config.prepend_backend_path if config is not None else (lambda path: path)
        env: dict[str, str] = {}
        for endpoint in Endpoint:
            url = base + prepend(str(endpoint))
            if endpoint == Endpoint.EVENT:
                url = url.replace("https://", "wss://").replace("http://", "ws://")
            env[endpoint.name] = url
        return env

    def post_build(self, **context) -> None:
        """Scaffold the Capacitor project (if needed) and copy in the static frontend.

        Args:
            context: Plugin context; ``static_dir`` is the built frontend
                (``.web/build/client``).
        """
        from reflex_base.utils import console

        static_dir = Path(context["static_dir"]).resolve()
        project_root = (Path.cwd() / self.capacitor_dir).resolve()
        www = project_root / self.web_dir

        if not (project_root / _SCAFFOLD_MARKER).exists():
            self._scaffold(project_root)
            console.info(f"reflex-capacitor: scaffolded Capacitor project at {project_root}")
        else:
            console.info(f"reflex-capacitor: reusing Capacitor project at {project_root}")

        self._configure(project_root)

        if www.exists():
            shutil.rmtree(www)
        shutil.copytree(static_dir, www)
        console.info(f"reflex-capacitor: copied static frontend into {www}")

        self._warn_if_cors_blocks()

    def _scaffold(self, project_root: Path) -> None:
        """Create a minimal Capacitor project from the bundled template."""
        template = Path(__file__).parent / "scaffold"
        if not template.is_dir():
            msg = f"reflex-capacitor: missing scaffold template at {template}"
            raise FileNotFoundError(msg)

        project_root.mkdir(parents=True, exist_ok=True)
        # Copy template files (do not wipe android/ios if somehow present).
        for path in template.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(template)
            dest = project_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)

        (project_root / self.web_dir).mkdir(parents=True, exist_ok=True)
        placeholder = project_root / self.web_dir / "index.html"
        if not placeholder.exists():
            placeholder.write_text(
                "<!doctype html><html><body><p>Run reflex-capacitor sync</p></body></html>\n",
                encoding="utf-8",
            )

        (project_root / _SCAFFOLD_MARKER).write_text("remote\n", encoding="utf-8")
        self._write_gitignore(project_root)

    def _configure(self, project_root: Path) -> None:
        """Apply rxconfig-driven settings to capacitor.config.json and package.json."""
        app_name, app_id = self._resolved_names()
        self._apply_capacitor_config(project_root / "capacitor.config.json", app_name, app_id)
        self._apply_package_json(project_root / "package.json", app_name)

    def _apply_capacitor_config(self, conf_path: Path, app_name: str, app_id: str) -> None:
        """Write / patch capacitor.config.json."""
        if conf_path.exists():
            conf = json.loads(conf_path.read_text(encoding="utf-8"))
        else:
            conf = {}
        conf["appId"] = app_id
        conf["appName"] = app_name
        conf["webDir"] = self.web_dir
        server = conf.setdefault("server", {})
        # Android blocks cleartext (http) by default from API 28+. Capacitor's
        # ``server.cleartext`` maps to ``android:usesCleartextTraffic`` on sync.
        #
        # Critical for LAN http backends: Capacitor defaults ``androidScheme`` to
        # ``https``, so the WebView origin is ``https://localhost``. A page on
        # https cannot open ``ws://…`` (mixed content) — the UI loads, then
        # ``cannot connect to server: timeout`` on ``/_event``. For http backends
        # we must use ``androidScheme: http`` so ``ws://`` is allowed.
        base = self._backend_base()
        if base and base.startswith("http://"):
            server["cleartext"] = True
            server["androidScheme"] = "http"
        elif base and base.startswith("https://"):
            server["cleartext"] = False
            server["androidScheme"] = "https"
        else:
            server.setdefault("androidScheme", "https")
        conf_path.write_text(json.dumps(conf, indent=2) + "\n", encoding="utf-8")

    def ensure_android_cleartext(self, project_root: Path | None = None) -> None:
        """Force ``usesCleartextTraffic`` when the backend is plain HTTP.

        Capacitor usually applies this from ``server.cleartext`` during ``cap sync``,
        but we patch the manifest as a safety net so LAN ``http://`` backends work.
        """
        base = self._backend_base()
        if not base or not base.startswith("http://"):
            return
        root = project_root or (Path.cwd() / self.capacitor_dir).resolve()
        manifest = root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
        if not manifest.is_file():
            return
        text = manifest.read_text(encoding="utf-8")
        if "usesCleartextTraffic" in text:
            return
        # Insert on the <application ...> opening tag.
        patched = text.replace(
            "<application",
            '<application\n        android:usesCleartextTraffic="true"',
            1,
        )
        if patched == text:
            return
        manifest.write_text(patched, encoding="utf-8")
        from reflex_base.utils import console

        console.info(
            "reflex-capacitor: enabled android:usesCleartextTraffic for http backend"
        )

    def _apply_package_json(self, pkg_path: Path, app_name: str) -> None:
        """Ensure core Capacitor dependencies are declared."""
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        else:
            pkg = {
                "name": slugify(app_name),
                "version": "0.1.0",
                "private": True,
            }
        pkg["name"] = slugify(app_name)
        deps = pkg.setdefault("dependencies", {})
        dev_deps = pkg.setdefault("devDependencies", {})
        deps["@capacitor/core"] = CAPACITOR_VERSION
        deps["@capacitor/android"] = CAPACITOR_VERSION
        deps["@capacitor/ios"] = CAPACITOR_VERSION
        dev_deps["@capacitor/cli"] = CAPACITOR_VERSION
        pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")

    def _write_gitignore(self, project_root: Path) -> None:
        """Write a .gitignore for Capacitor build artifacts."""
        entries = [
            "node_modules/",
            f"{self.web_dir}/",
            "android/.gradle/",
            "android/app/build/",
            "android/build/",
            "android/local.properties",
            "ios/App/Pods/",
            "ios/DerivedData/",
        ]
        (project_root / ".gitignore").write_text("\n".join(entries) + "\n", encoding="utf-8")

    def _warn_if_cors_blocks(self) -> None:
        """Warn when CORS would block the Capacitor WebView origin."""
        from reflex_base.config import get_config
        from reflex_base.utils import console

        config = get_config()
        if config is None:
            return
        origins = tuple(config.cors_allowed_origins)
        if "*" in origins or any(o in origins for o in CAPACITOR_ORIGINS):
            return
        console.warn(
            "reflex-capacitor: cors_allowed_origins does not include Capacitor WebView "
            f"origins ({', '.join(CAPACITOR_ORIGINS)}). The app may fail to reach the "
            'backend. Set cors_allowed_origins=["*"] or add those origins in rxconfig.'
        )


# Used by CLI helpers; keep a simple regex for validating app ids.
_APP_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$", re.I)


def is_valid_app_id(app_id: str) -> bool:
    """Return whether ``app_id`` looks like a reverse-DNS identifier."""
    return bool(_APP_ID_RE.match(app_id))
