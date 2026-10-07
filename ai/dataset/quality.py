"""Image quality analysis — real measurements plus configurable heuristics.

MEASUREMENTS (actual calculations):
- blur_score     variance of the Laplacian on the grayscale image
- brightness_*   mean / std / min / max of grayscale intensity (0-255)
- aspect_ratio   width / height
- resolution     width, height, pixel count, minimum dimension

HEURISTICS (configurable thresholds from configs/project.yaml, not ground truth):
- flags such as blur_review / too_dark / low_resolution
- the overall PASS / REVIEW / FAIL status derived from status_rules
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import cv2
import numpy as np

from ai.dataset.models import (
    FAIL,
    PASS,
    REVIEW,
    ManifestRecord,
    QualityRecord,
    QualitySummary,
)
from ai.dataset.settings import QualitySettings

FLAG_DECODE_FAILED = "decode_failed"
FLAG_BLUR_FAIL = "blur_fail"
FLAG_BLUR_REVIEW = "blur_review"
FLAG_LOW_RESOLUTION = "low_resolution"
FLAG_TOO_DARK = "too_dark"
FLAG_TOO_BRIGHT = "too_bright"
FLAG_EXTREME_ASPECT = "extreme_aspect_ratio"
FLAG_EXACT_DUPLICATE = "exact_duplicate"
FLAG_SUSPICIOUS_DUPLICATE = "suspicious_duplicate"


@dataclass
class RawQualityMetrics:
    """Measurements taken while the image pixels are in memory."""

    blur_score: float | None
    brightness_mean: float | None
    brightness_std: float | None
    brightness_min: float | None
    brightness_max: float | None
    aspect_ratio: float | None
    pixel_count: int | None
    min_dimension: int | None


def measure_quality(gray: np.ndarray, record: ManifestRecord) -> RawQualityMetrics:
    """Compute all pixel measurements for one decoded image."""
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness_mean = float(gray.mean())
    brightness_std = float(gray.std())
    brightness_min = float(gray.min())
    brightness_max = float(gray.max())

    width = record.width or 0
    height = record.height or 0
    aspect_ratio = (width / height) if height else None
    pixel_count = width * height
    min_dimension = min(width, height) if width and height else None

    return RawQualityMetrics(
        blur_score=blur_score,
        brightness_mean=brightness_mean,
        brightness_std=brightness_std,
        brightness_min=brightness_min,
        brightness_max=brightness_max,
        aspect_ratio=aspect_ratio,
        pixel_count=pixel_count,
        min_dimension=min_dimension,
    )


def compute_flags(
    record: ManifestRecord, metrics: RawQualityMetrics | None, settings: QualitySettings
) -> list[str]:
    """Derive quality flags from measurements and duplicate status."""
    if not record.readable or metrics is None:
        return [FLAG_DECODE_FAILED]

    flags: list[str] = []

    if metrics.min_dimension is not None and (
        (record.width or 0) < settings.min_width or (record.height or 0) < settings.min_height
    ):
        flags.append(FLAG_LOW_RESOLUTION)

    if metrics.blur_score is not None:
        if metrics.blur_score < settings.blur.fail_threshold:
            flags.append(FLAG_BLUR_FAIL)
        elif metrics.blur_score < settings.blur.review_threshold:
            flags.append(FLAG_BLUR_REVIEW)

    if metrics.brightness_mean is not None:
        if metrics.brightness_mean < settings.brightness.dark_threshold:
            flags.append(FLAG_TOO_DARK)
        elif metrics.brightness_mean > settings.brightness.bright_threshold:
            flags.append(FLAG_TOO_BRIGHT)

    if metrics.aspect_ratio is not None and not (
        settings.aspect_ratio.min <= metrics.aspect_ratio <= settings.aspect_ratio.max
    ):
        flags.append(FLAG_EXTREME_ASPECT)

    if record.is_exact_duplicate:
        flags.append(FLAG_EXACT_DUPLICATE)
    if record.is_suspicious_duplicate:
        flags.append(FLAG_SUSPICIOUS_DUPLICATE)

    return flags


def derive_status(flags: list[str], settings: QualitySettings) -> str:
    """FAIL if any fail-severity flag, else REVIEW if any review flag, else PASS."""
    if any(flag in settings.status_rules.fail_flags for flag in flags):
        return FAIL
    if any(flag in settings.status_rules.review_flags for flag in flags):
        return REVIEW
    return PASS


def file_size_fields(size_bytes: int) -> dict[str, float]:
    return {
        "file_size_bytes": size_bytes,
        "file_size_kb": round(size_bytes / 1024, 2),
        "file_size_mb": round(size_bytes / (1024 * 1024), 3),
    }


def finalize_quality(
    record: ManifestRecord,
    metrics: RawQualityMetrics | None,
    settings: QualitySettings,
) -> QualityRecord:
    """Build the persisted quality record (after duplicate flags are known)."""
    flags = compute_flags(record, metrics, settings)
    status = derive_status(flags, settings)
    m = metrics

    return QualityRecord(
        image_id=record.image_id,
        source_relative_path=record.source_relative_path,
        class_name=record.class_name,
        quality_status=status,
        flags=flags,
        width=record.width,
        height=record.height,
        pixel_count=m.pixel_count if m else None,
        min_dimension=m.min_dimension if m else None,
        aspect_ratio=round(m.aspect_ratio, 4) if m and m.aspect_ratio is not None else None,
        blur_score=round(m.blur_score, 2) if m and m.blur_score is not None else None,
        brightness_mean=round(m.brightness_mean, 2)
        if m and m.brightness_mean is not None
        else None,
        brightness_std=round(m.brightness_std, 2) if m and m.brightness_std is not None else None,
        brightness_min=m.brightness_min if m else None,
        brightness_max=m.brightness_max if m else None,
        color_mode=record.color_mode,
        channels=record.channels,
        **file_size_fields(record.file_size_bytes),
        sha256=record.sha256,
        is_exact_duplicate=record.is_exact_duplicate,
        duplicate_group_id=record.duplicate_group_id,
        is_suspicious_duplicate=record.is_suspicious_duplicate,
    )


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "mean": None, "max": None}
    return {
        "min": round(min(values), 2),
        "median": round(statistics.median(values), 2),
        "mean": round(statistics.fmean(values), 2),
        "max": round(max(values), 2),
    }


def thresholds_payload(settings: QualitySettings) -> dict:
    """The exact thresholds applied to a report (recorded for reproducibility)."""
    return {
        "note": "Configurable heuristics from configs/project.yaml — not ground truth.",
        "min_width": settings.min_width,
        "min_height": settings.min_height,
        "blur_method": settings.blur.method,
        "blur_review_threshold": settings.blur.review_threshold,
        "blur_fail_threshold": settings.blur.fail_threshold,
        "brightness_dark_threshold": settings.brightness.dark_threshold,
        "brightness_bright_threshold": settings.brightness.bright_threshold,
        "aspect_ratio_min": settings.aspect_ratio.min,
        "aspect_ratio_max": settings.aspect_ratio.max,
        "fail_flags": settings.status_rules.fail_flags,
        "review_flags": settings.status_rules.review_flags,
    }


def build_quality_summary(
    records: list[QualityRecord], settings: QualitySettings
) -> QualitySummary:
    """Aggregate real counts and distributions from measured quality records."""
    blur_scores = [r.blur_score for r in records if r.blur_score is not None]
    brightness_values = [r.brightness_mean for r in records if r.brightness_mean is not None]

    flag_counts: dict[str, int] = {}
    for record in records:
        for flag in record.flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    fail_t = settings.blur.fail_threshold
    review_t = settings.blur.review_threshold
    dark_t = settings.brightness.dark_threshold
    bright_t = settings.brightness.bright_threshold

    blur_distribution = {
        f"fail(<{fail_t:g})": sum(1 for s in blur_scores if s < fail_t),
        f"review({fail_t:g}-{review_t:g})": sum(1 for s in blur_scores if fail_t <= s < review_t),
        f"pass(>={review_t:g})": sum(1 for s in blur_scores if s >= review_t),
        "n/a": len(records) - len(blur_scores),
    }
    brightness_distribution = {
        f"dark(<{dark_t:g})": sum(1 for b in brightness_values if b < dark_t),
        "normal": sum(1 for b in brightness_values if dark_t <= b <= bright_t),
        f"bright(>{bright_t:g})": sum(1 for b in brightness_values if b > bright_t),
        "n/a": len(records) - len(brightness_values),
    }

    resolution_counts: dict[str, int] = {}
    for record in records:
        key = f"{record.width}x{record.height}" if record.width and record.height else "n/a"
        resolution_counts[key] = resolution_counts.get(key, 0) + 1

    pass_count = sum(1 for r in records if r.quality_status == PASS)
    review_count = sum(1 for r in records if r.quality_status == REVIEW)
    fail_count = sum(1 for r in records if r.quality_status == FAIL)

    return QualitySummary(
        total=len(records),
        pass_count=pass_count,
        review_count=review_count,
        fail_count=fail_count,
        flagged_count=review_count + fail_count,
        flag_counts=dict(sorted(flag_counts.items())),
        blur_statistics=_stats([float(s) for s in blur_scores]),
        brightness_statistics=_stats([float(b) for b in brightness_values]),
        blur_distribution=blur_distribution,
        brightness_distribution=brightness_distribution,
        resolution_distribution=dict(sorted(resolution_counts.items())),
        low_resolution_count=flag_counts.get(FLAG_LOW_RESOLUTION, 0),
        exact_duplicate_images=sum(1 for r in records if r.is_exact_duplicate),
        suspicious_duplicate_images=sum(1 for r in records if r.is_suspicious_duplicate),
    )
