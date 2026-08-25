"""Network env for CLI child processes (npm / Gradle).

By default reflex-capacitor does **not** use a proxy: ambient ``http_proxy`` /
``HTTPS_PROXY`` / etc. are stripped so a broken system proxy cannot slow or
break installs. Pass ``--proxy`` or set ``REFLEX_CAPACITOR_PROXY`` to opt in.
"""

from __future__ import annotations

import os
from typing import Final
from urllib.parse import urlparse

# Env var accepted by Click ``--proxy`` (and documented for scripts/CI).
PROXY_ENV_VAR: Final = "REFLEX_CAPACITOR_PROXY"

_PROXY_ENV_KEYS: Final[tuple[str, ...]] = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "ALL_PROXY",
    "ftp_proxy",
    "FTP_PROXY",
)


def normalize_proxy_url(proxy: str) -> str:
    """Ensure the proxy string has a scheme (default ``http://``)."""
    text = proxy.strip()
    if not text:
        raise ValueError("proxy URL is empty")
    if "://" not in text:
        text = f"http://{text}"
    return text


def parse_proxy_host_port(proxy: str) -> tuple[str, int]:
    """Parse host and port from a proxy URL for JVM ``-Dhttp.proxyHost`` flags."""
    parsed = urlparse(normalize_proxy_url(proxy))
    host = parsed.hostname
    if not host:
        raise ValueError(f"invalid proxy URL (no host): {proxy!r}")
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return host, port


def gradle_jvm_proxy_args(proxy: str) -> list[str]:
    """Return ``-D…`` args so the Gradle JVM uses the given proxy."""
    host, port = parse_proxy_host_port(proxy)
    return [
        f"-Dhttp.proxyHost={host}",
        f"-Dhttp.proxyPort={port}",
        f"-Dhttps.proxyHost={host}",
        f"-Dhttps.proxyPort={port}",
    ]


def child_env(*, proxy: str | None = None, base: dict[str, str] | None = None) -> dict[str, str]:
    """Build env for npm/Gradle: clear ambient proxies, optionally set one.

    Args:
        proxy: Explicit proxy URL, or ``None`` for no proxy.
        base: Starting env (default: ``os.environ``).
    """
    env = dict(base if base is not None else os.environ)
    for key in _PROXY_ENV_KEYS:
        env.pop(key, None)

    if not proxy:
        return env

    url = normalize_proxy_url(proxy)
    env["http_proxy"] = url
    env["https_proxy"] = url
    env["HTTP_PROXY"] = url
    env["HTTPS_PROXY"] = url

    # Gradle / Java often ignore shell proxy vars; append JVM system props.
    jvm = " ".join(gradle_jvm_proxy_args(url))
    existing = env.get("GRADLE_OPTS", "").strip()
    env["GRADLE_OPTS"] = f"{existing} {jvm}".strip() if existing else jvm
    return env
