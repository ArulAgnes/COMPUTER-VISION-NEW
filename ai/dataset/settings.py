"""Engine-side configuration models for dataset discovery and quality analysis.

These are the canonical models for the ``quality`` and ``duplicates`` sections
of ``configs/project.yaml``. The application configuration imports them, so a
single definition is shared by the CLI, the API and the engine itself.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ClassDef(BaseModel):
    """A detector class as seen by the engine (id + name)."""

    id: int = Field(ge=0)
    name: str = Field(min_length=1)


class BlurSettings(BaseModel):
    """Blur measurement settings (Laplacian variance on grayscale)."""

    method: str = "laplacian_variance"
    review_threshold: float = Field(gt=0)
    fail_threshold: float = Field(gt=0)

    @model_validator(mode="after")
    def thresholds_ordered(self) -> "BlurSettings":
        if self.fail_threshold > self.review_threshold:
            raise ValueError("quality.blur.fail_threshold must be <= review_threshold")
        return self


class BrightnessSettings(BaseModel):
    """Brightness thresholds on mean grayscale intensity (0-255)."""

    dark_threshold: float = Field(ge=0, le=255)
    bright_threshold: float = Field(ge=0, le=255)

    @model_validator(mode="after")
    def thresholds_ordered(self) -> "BrightnessSettings":
        if self.dark_threshold >= self.bright_threshold:
            raise ValueError("quality.brightness.dark_threshold must be < bright_threshold")
        return self


class AspectRatioSettings(BaseModel):
    """Accepted width/height range."""

    min: float = Field(gt=0)
    max: float = Field(gt=0)

    @model_validator(mode="after")
    def range_valid(self) -> "AspectRatioSettings":
        if self.min >= self.max:
            raise ValueError("quality.aspect_ratio.min must be < max")
        return self


class StatusRules(BaseModel):
    """Maps quality flags to the overall status.

    Severity order: any flag in ``fail_flags`` => FAIL,
    else any flag in ``review_flags`` => REVIEW, else PASS.
    """

    fail_flags: list[str]
    review_flags: list[str]


class QualitySettings(BaseModel):
    """All quality-engine thresholds (configurable heuristics)."""

    min_width: int = Field(gt=0)
    min_height: int = Field(gt=0)
    blur: BlurSettings
    brightness: BrightnessSettings
    aspect_ratio: AspectRatioSettings
    status_rules: StatusRules


class NearDuplicateSettings(BaseModel):
    """Near-duplicate detection via 64-bit difference hash."""

    enabled: bool
    method: str
    max_hamming_distance: int = Field(ge=0, le=64)


class DuplicateSettings(BaseModel):
    """Duplicate detection configuration (exact detection always uses SHA-256)."""

    near_duplicate: NearDuplicateSettings
