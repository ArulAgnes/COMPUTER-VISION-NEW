"""Dashboard status schema.

Every pipeline value is ``null`` until the corresponding stage actually
produces it. The frontend renders ``null`` as "Not available".
"""

from __future__ import annotations

from pydantic import BaseModel


class Stage0Baseline(BaseModel):
    """Facts measured by the read-only Stage 0 raw data audit."""

    source: str | None
    stage: str | None
    audited_at: str | None
    total_images: int | None
    class_counts: dict[str, int] | None


class EvaluationStatus(BaseModel):
    """Real evaluation results — null until an evaluation has run."""

    status: str
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    map: float | None = None


class PipelineStatus(BaseModel):
    """Counts and versions produced by later pipeline stages."""

    dataset_version: str | None = None
    annotated_images: int | None = None
    train_images: int | None = None
    validation_images: int | None = None
    test_images: int | None = None
    model_version: str | None = None
    evaluation: EvaluationStatus


class StatusResponse(BaseModel):
    stage0_baseline: Stage0Baseline | None = None
    pipeline: PipelineStatus
