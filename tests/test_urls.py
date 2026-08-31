"""Tests for Capacitor-aware upload / backend URL helpers."""

from __future__ import annotations

import os

import pytest

from reflex_capacitor.config import DEV_BACKEND_URL_ENV
from reflex_capacitor.plugin import CapacitorPlugin
from reflex_capacitor.urls import get_upload_url, resolve_backend_base


def test_resolve_backend_base_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEV_BACKEND_URL_ENV, "http://192.168.1.56:8003/")
    assert resolve_backend_base() == "http://192.168.1.56:8003"


def test_resolve_backend_base_uses_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEV_BACKEND_URL_ENV, raising=False)

    class _Cfg:
        api_url = "http://localhost:8000"
        plugins = [CapacitorPlugin(backend_url="http://10.0.0.2:8001")]

    monkeypatch.setattr("reflex_base.config.get_config", lambda: _Cfg())
    assert resolve_backend_base() == "http://10.0.0.2:8001"


def test_get_upload_url_joins_upload_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEV_BACKEND_URL_ENV, "http://192.168.1.56:8003")
    url = get_upload_url("sample.mp3")
    assert url == "http://192.168.1.56:8003/_upload/sample.mp3"
    assert "localhost" not in url
