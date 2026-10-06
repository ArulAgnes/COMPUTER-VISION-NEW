"""Public configuration response schema (safe to expose to the frontend)."""

from __future__ import annotations

from pydantic import BaseModel


class ClassOut(BaseModel):
    id: int
    name: str


class SplitOut(BaseModel):
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    seed: int
    stratified: bool


class ThresholdsOut(BaseModel):
    confidence: float
    nms: float
    iou: float


class EvaluationOut(BaseModel):
    iou_threshold: float
    target_map: float | None
    target_f1: float | None


class TrainingOut(BaseModel):
    epochs: int
    batch_size: int
    learning_rate: float
    seed: int


class PublicConfigResponse(BaseModel):
    """Configuration values read from configs/project.yaml.

    These are settings, not results — no metrics are included.
    """

    project_name: str
    project_version: str
    classes: list[ClassOut]
    num_classes: int
    image_size: int
    split: SplitOut
    thresholds: ThresholdsOut
    evaluation: EvaluationOut
    training: TrainingOut
