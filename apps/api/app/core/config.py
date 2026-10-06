"""Central configuration loading.

All project settings come from ``configs/project.yaml``. Environment
variables provide genuine environment-specific overrides only:

- ``CV_CONFIG``        absolute path to an alternative config file
- ``CV_PROJECT_ROOT``  project root (defaults to the repository root)
- ``CV_RAW_DATA_DIR``  raw dataset directory (read-only source images)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

# apps/api/app/core/config.py -> parents: core, app, api, apps, repo root
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_FILE = "configs/project.yaml"


class ProjectMeta(BaseModel):
    """Project identity."""

    name: str
    version: str


class ClassConfig(BaseModel):
    """A single detector class. The class list defines num_classes."""

    id: int = Field(ge=0, description="Zero-based class id")
    name: str = Field(min_length=1)


class PathsConfig(BaseModel):
    """Filesystem layout. ``raw_data_dir`` is read-only; everything else is
    generated inside the project repository and relative to the project root."""

    raw_data_dir: str
    data_dir: str
    manifests_dir: str
    annotations_dir: str
    datasets_dir: str
    versions_dir: str
    augmented_dir: str
    reports_dir: str
    models_dir: str
    checkpoints_dir: str
    registry_dir: str
    logs_dir: str
    baseline_file: str


class ImageConfig(BaseModel):
    """Detector input size."""

    size: int = Field(gt=0)


class SplitConfig(BaseModel):
    """Deterministic original-image split (Stage 4)."""

    train_ratio: float = Field(gt=0, lt=1)
    validation_ratio: float = Field(gt=0, lt=1)
    test_ratio: float = Field(gt=0, lt=1)
    seed: int
    stratified: bool

    @model_validator(mode="after")
    def ratios_sum_to_one(self) -> "SplitConfig":
        total = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"split ratios must sum to 1.0, got {total:.6f}")
        return self


class TrainingConfig(BaseModel):
    """From-scratch training parameters (Stage 7). No pretrained weights."""

    epochs: int = Field(gt=0)
    batch_size: int = Field(gt=0)
    learning_rate: float = Field(gt=0)
    num_workers: int = Field(ge=0)
    seed: int


class ThresholdsConfig(BaseModel):
    """Inference post-processing thresholds."""

    confidence: float = Field(gt=0, lt=1)
    nms: float = Field(gt=0, lt=1)
    iou: float = Field(gt=0, lt=1)


class EvaluationTargets(BaseModel):
    """Configured TARGETS. These are goals, never achieved results."""

    map: float | None
    f1: float | None


class EvaluationConfig(BaseModel):
    """Evaluation settings (Stage 8)."""

    iou_threshold: float = Field(gt=0, lt=1)
    targets: EvaluationTargets


class QualityConfig(BaseModel):
    """Image quality thresholds (Stage 2)."""

    min_blur_score: float = Field(ge=0)
    min_brightness: float = Field(ge=0)
    max_brightness: float = Field(gt=0)
    min_width: int = Field(gt=0)
    min_height: int = Field(gt=0)

    @model_validator(mode="after")
    def brightness_range_valid(self) -> "QualityConfig":
        if self.min_brightness >= self.max_brightness:
            raise ValueError("quality.min_brightness must be < quality.max_brightness")
        return self


class AugmentationConfig(BaseModel):
    """Train-only augmentation settings (Stage 5)."""

    enabled: bool
    seed: int


class Settings(BaseModel):
    """Root configuration object."""

    project: ProjectMeta
    classes: list[ClassConfig]
    paths: PathsConfig
    image: ImageConfig
    split: SplitConfig
    training: TrainingConfig
    thresholds: ThresholdsConfig
    evaluation: EvaluationConfig
    quality: QualityConfig
    augmentation: AugmentationConfig

    @model_validator(mode="after")
    def classes_valid(self) -> "Settings":
        if not self.classes:
            raise ValueError("at least one class must be configured")
        ids = [c.id for c in self.classes]
        names = [c.name for c in self.classes]
        if len(set(ids)) != len(ids):
            raise ValueError(f"class ids must be unique, got {ids}")
        if sorted(ids) != list(range(len(ids))):
            raise ValueError(f"class ids must be contiguous starting at 0, got {ids}")
        if len(set(names)) != len(names):
            raise ValueError(f"class names must be unique, got {names}")
        return self

    @property
    def num_classes(self) -> int:
        """Number of classes derived from configuration (never hardcoded)."""
        return len(self.classes)

    @property
    def class_names(self) -> list[str]:
        return [c.name for c in sorted(self.classes, key=lambda c: c.id)]


def project_root() -> Path:
    """Resolve the project root directory."""
    env_root = os.environ.get("CV_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return DEFAULT_PROJECT_ROOT.resolve()


def load_settings(config_file: Path | None = None) -> Settings:
    """Load and validate configuration from YAML with environment overrides."""
    if config_file is None:
        env_config = os.environ.get("CV_CONFIG")
        config_file = Path(env_config) if env_config else project_root() / DEFAULT_CONFIG_FILE

    config_file = Path(config_file).expanduser().resolve()
    if not config_file.is_file():
        raise FileNotFoundError(f"configuration file not found: {config_file}")

    with config_file.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"configuration file must contain a mapping: {config_file}")

    raw_override = os.environ.get("CV_RAW_DATA_DIR")
    if raw_override:
        data.setdefault("paths", {})["raw_data_dir"] = raw_override

    return Settings.model_validate(data)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance (process-wide)."""
    return load_settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests)."""
    get_settings.cache_clear()
