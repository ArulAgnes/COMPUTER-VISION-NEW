"""Configuration loading and validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import get_settings, load_settings, project_root
from app.core.paths import raw_data_dir


def test_config_file_exists() -> None:
    assert (project_root() / "configs" / "project.yaml").is_file()
    assert (project_root() / "configs" / "stage0_baseline.json").is_file()


def test_classes_are_bell_and_oillamp() -> None:
    settings = get_settings()
    assert settings.class_names == ["bell", "oillamp"]
    assert [c.id for c in settings.classes] == [0, 1]
    assert settings.num_classes == 2  # derived from configuration, not hardcoded


def test_split_ratios_sum_to_one() -> None:
    split = get_settings().split
    assert abs(split.train_ratio + split.validation_ratio + split.test_ratio - 1.0) < 1e-6


def test_seed_is_configured() -> None:
    settings = get_settings()
    assert isinstance(settings.split.seed, int)
    assert isinstance(settings.training.seed, int)


def test_paths_configured_separately() -> None:
    settings = get_settings()
    assert settings.paths.raw_data_dir != settings.paths.data_dir
    assert "captured_photos" in settings.paths.raw_data_dir


def test_raw_data_is_outside_project_root() -> None:
    raw = raw_data_dir()
    assert not raw.is_relative_to(project_root()), "raw dataset must live outside the repo"


def test_raw_data_dir_is_readonly_by_convention() -> None:
    """Raw path is a distinct configured path, never a generated directory."""
    from app.core.paths import generated_dir_names

    assert "raw_data_dir" not in generated_dir_names()


def test_invalid_split_ratios_rejected(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
project: {name: x, version: "0"}
classes: [{id: 0, name: bell}]
paths:
  raw_data_dir: /tmp/raw
  data_dir: data
  manifests_dir: data/manifests
  annotations_dir: data/annotations
  datasets_dir: data/datasets
  versions_dir: data/versions
  augmented_dir: data/augmented
  reports_dir: data/reports
  models_dir: models
  checkpoints_dir: models/checkpoints
  registry_dir: models/registry
  logs_dir: logs
  baseline_file: configs/stage0_baseline.json
image: {size: 640}
split: {train_ratio: 0.9, validation_ratio: 0.05, test_ratio: 0.02, seed: 1, stratified: true}
training: {epochs: 1, batch_size: 1, learning_rate: 0.001, num_workers: 0, seed: 1}
thresholds: {confidence: 0.25, nms: 0.45, iou: 0.5}
evaluation: {iou_threshold: 0.5, targets: {map: null, f1: null}}
quality: {min_blur_score: 50, min_brightness: 40, max_brightness: 220, min_width: 64, min_height: 64}
augmentation: {enabled: false, seed: 1}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_settings(bad)


def test_duplicate_class_ids_rejected() -> None:
    settings = get_settings().model_copy(deep=True)
    data = settings.model_dump()
    data["classes"] = [{"id": 0, "name": "bell"}, {"id": 0, "name": "oillamp"}]
    with pytest.raises(ValidationError):
        type(settings).model_validate(data)
