"""Public configuration endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.config import (
    ClassOut,
    EvaluationOut,
    PublicConfigResponse,
    SplitOut,
    ThresholdsOut,
    TrainingOut,
)

router = APIRouter()


@router.get("/api/config", response_model=PublicConfigResponse, tags=["config"])
def get_public_config() -> PublicConfigResponse:
    """Configuration values from configs/project.yaml (settings, not results)."""
    settings = get_settings()
    return PublicConfigResponse(
        project_name=settings.project.name,
        project_version=settings.project.version,
        classes=[ClassOut(id=c.id, name=c.name) for c in settings.classes],
        num_classes=settings.num_classes,
        image_size=settings.image.size,
        split=SplitOut(
            train_ratio=settings.split.train_ratio,
            validation_ratio=settings.split.validation_ratio,
            test_ratio=settings.split.test_ratio,
            seed=settings.split.seed,
            stratified=settings.split.stratified,
        ),
        thresholds=ThresholdsOut(
            confidence=settings.thresholds.confidence,
            nms=settings.thresholds.nms,
            iou=settings.thresholds.iou,
        ),
        evaluation=EvaluationOut(
            iou_threshold=settings.evaluation.iou_threshold,
            target_map=settings.evaluation.targets.map,
            target_f1=settings.evaluation.targets.f1,
        ),
        training=TrainingOut(
            epochs=settings.training.epochs,
            batch_size=settings.training.batch_size,
            learning_rate=settings.training.learning_rate,
            seed=settings.training.seed,
        ),
    )
