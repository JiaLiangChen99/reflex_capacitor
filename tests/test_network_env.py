"""Unit tests for CLI network / proxy helpers."""

from __future__ import annotations

import pytest

from reflex_capacitor.network_env import (
    child_env,
    gradle_jvm_proxy_args,
    normalize_proxy_url,
    parse_proxy_host_port,
)


def test_normalize_adds_http_scheme() -> None:
    assert normalize_proxy_url("127.0.0.1:7890") == "http://127.0.0.1:7890"
    assert normalize_proxy_url("http://proxy:8080") == "http://proxy:8080"


def test_parse_host_port() -> None:
    assert parse_proxy_host_port("http://192.168.1.1:7892") == ("192.168.1.1", 7892)
    assert parse_proxy_host_port("proxy.example:3128") == ("proxy.example", 3128)


def test_child_env_strips_ambient_when_no_proxy() -> None:
    base = {
        "PATH": "/usr/bin",
        "http_proxy": "http://evil:1",
        "HTTPS_PROXY": "http://evil:1",
        "HOME": "/tmp",
    }
    out = child_env(proxy=None, base=base)
    assert "http_proxy" not in out
    assert "HTTPS_PROXY" not in out
    assert out["PATH"] == "/usr/bin"
    assert out["HOME"] == "/tmp"


def test_child_env_sets_proxy_and_gradle_opts() -> None:
    out = child_env(proxy="127.0.0.1:7890", base={"PATH": "/bin"})
    assert out["http_proxy"] == "http://127.0.0.1:7890"
    assert out["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert "-Dhttp.proxyHost=127.0.0.1" in out["GRADLE_OPTS"]
    assert "-Dhttp.proxyPort=7892" in out["GRADLE_OPTS"]


def test_gradle_jvm_proxy_args() -> None:
    args = gradle_jvm_proxy_args("http://host:9")
    assert args == [
        "-Dhttp.proxyHost=host",
        "-Dhttp.proxyPort=9",
        "-Dhttps.proxyHost=host",
        "-Dhttps.proxyPort=9",
    ]


def test_empty_proxy_raises() -> None:
    with pytest.raises(ValueError):
        normalize_proxy_url("   ")
