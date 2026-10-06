"""Raw-data protection and generated path tests."""

from __future__ import annotations

import pytest

from app.core.paths import (
    RawDataViolationError,
    assert_not_raw,
    ensure_generated_dirs,
    generated_dir,
    is_raw_path,
    raw_data_dir,
)


def test_raw_dir_exists_and_is_distinct() -> None:
    raw = raw_data_dir()
    assert raw.is_dir(), f"raw data dir missing: {raw}"
    assert generated_dir("data_dir") != raw


def test_is_raw_path_detects_raw_children() -> None:
    raw = raw_data_dir()
    assert is_raw_path(raw) is True
    assert is_raw_path(raw / "bell" / "example.jpeg") is True


def test_is_raw_path_false_for_generated_dirs() -> None:
    assert is_raw_path(generated_dir("data_dir")) is False
    assert is_raw_path(generated_dir("checkpoints_dir")) is False


def test_assert_not_raw_raises_for_raw_path() -> None:
    with pytest.raises(RawDataViolationError):
        assert_not_raw(raw_data_dir() / "bell" / "photo.jpeg")


def test_assert_not_raw_allows_generated_path() -> None:
    assert_not_raw(generated_dir("annotations_dir"))


def test_generated_dir_rejects_raw_key() -> None:
    with pytest.raises(ValueError):
        generated_dir("raw_data_dir")


def test_ensure_generated_dirs_is_idempotent() -> None:
    ensure_generated_dirs()
    created_second = ensure_generated_dirs()
    assert created_second == []
    for name in ("manifests_dir", "annotations_dir", "datasets_dir", "checkpoints_dir"):
        assert generated_dir(name).is_dir()
