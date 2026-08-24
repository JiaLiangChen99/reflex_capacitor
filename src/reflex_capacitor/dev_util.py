"""Helpers for ``reflex-capacitor dev`` (LAN IP, port waits)."""

from __future__ import annotations

import socket
import subprocess
import time
import urllib.error
import urllib.request


def guess_lan_ip() -> str:
    """Best-effort LAN IPv4 for phone → dev machine connectivity."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def wait_for_port(port: int, proc: subprocess.Popen | None, *, timeout: float = 120.0) -> None:
    """Block until ``port`` accepts TCP connections or the child process exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            msg = f"reflex process exited with code {proc.returncode} before port {port} opened"
            raise RuntimeError(msg)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                return
        except OSError:
            time.sleep(0.4)
    msg = f"timed out waiting for port {port}"
    raise RuntimeError(msg)


def wait_for_http_ok(url: str, proc: subprocess.Popen | None, *, timeout: float = 120.0) -> None:
    """Block until ``url`` returns HTTP 200."""
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            msg = f"reflex process exited with code {proc.returncode} before {url} was ready"
            raise RuntimeError(msg)
        try:
            with urllib.request.urlopen(url, timeout=1.5) as response:
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    msg = f"timed out waiting for {url}"
    if last_error:
        msg += f" (last error: {last_error})"
    raise RuntimeError(msg)
