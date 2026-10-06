"""Builds the dashboard status payload from real project state.

There are no metric calculators here. Values that have not been produced by
an actual pipeline stage remain ``None`` so the frontend can show
"Not available" instead of a fabricated number.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings, project_root
from app.core.logging import get_logger
from app.core.paths import generated_dir, generated_dir_names
from app.schemas.status import (
    EvaluationStatus,
    PipelineStatus,
    Stage0Baseline,
    StatusResponse,
)

logger = get_logger("status")

NOT_EVALUATED = "not_evaluated_yet"


def load_baseline() -> Stage0Baseline | None:
    """Load the Stage 0 audit record written by the read-only baseline scan."""
    baseline_path: Path = project_root() / get_settings().paths.baseline_file
    if not baseline_path.is_file():
        logger.warning("stage 0 baseline file missing: %s", baseline_path)
        return None
    try:
        with baseline_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("could not read stage 0 baseline: %s", exc)
        return None

    return Stage0Baseline(
        source=data.get("source"),
        stage=data.get("stage"),
        audited_at=data.get("audited_at"),
        total_images=data.get("total_images"),
        class_counts=data.get("class_counts"),
    )


def get_status() -> StatusResponse:
    """Current platform status. Unproduced values stay None."""
    pipeline = PipelineStatus(
        dataset_version=None,
        annotated_images=None,
        train_images=None,
        validation_images=None,
        test_images=None,
        model_version=None,
        evaluation=EvaluationStatus(status=NOT_EVALUATED),
    )
    return StatusResponse(stage0_baseline=load_baseline(), pipeline=pipeline)


def generated_directories_exist() -> dict[str, bool]:
    """Existence of each generated directory (real filesystem check)."""
    return {name: generated_dir(name).is_dir() for name in generated_dir_names()}


__all__ = ["get_status", "load_baseline", "generated_directories_exist", "NOT_EVALUATED"]
