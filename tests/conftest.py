"""Shared pytest fixtures for reflex-capacitor tests."""

from __future__ import annotations

from pathlib import Path

import pytest

@pytest.fixture
def app_root(tmp_path: Path) -> Path:
    """Isolated app root directory (chdir target for plugin methods)."""
    return tmp_path
