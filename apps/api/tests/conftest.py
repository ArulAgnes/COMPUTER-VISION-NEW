"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings, project_root
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """Test client bound to a freshly created application."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def settings():
    """Project settings loaded from configs/project.yaml."""
    return get_settings()


@pytest.fixture()
def raw_dir() -> Path:
    """Read-only raw dataset directory (tests only ever read from it)."""
    return Path(get_settings().paths.raw_data_dir).expanduser().resolve()


@pytest.fixture()
def stage0_baseline() -> dict:
    """Measured Stage 0 facts (configs/stage0_baseline.json)."""
    path = project_root() / "configs" / "stage0_baseline.json"
    return json.loads(path.read_text(encoding="utf-8"))
