"""Dataset Stage 2 request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, create_model

from ai.dataset.models import (
    ManifestRecord,
    ManifestSummary,
    QualityRecord,
    QualitySummary,
    SuspiciousDuplicatePair,
)

# Manifest record without the absolute filesystem path (never expose raw paths).
ManifestRecordPublic = create_model(
    "ManifestRecordPublic",
    **{
        name: (info.annotation, info)
        for name, info in ManifestRecord.model_fields.items()
        if name != "source_path"
    },
)


class ImageListItem(BaseModel):
    """One row of the dataset grid: manifest fields joined with quality status."""

    image_id: str
    filename: str
    source_relative_path: str
    class_name: str | None
    class_id: int | None
    width: int | None
    height: int | None
    channels: int | None
    color_mode: str | None
    file_size_bytes: int
    extension: str
    readable: bool
    status: str
    is_exact_duplicate: bool
    duplicate_group_id: str | None
    is_suspicious_duplicate: bool
    quality_status: str | None
    flags: list[str]


class ImageListResponse(BaseModel):
    items: list[ImageListItem]
    total: int
    page: int
    page_size: int


class ImageDetailResponse(BaseModel):
    record: ManifestRecordPublic
    quality: QualityRecord | None


class DatasetSummaryResponse(BaseModel):
    """Discovery summary for the dashboard (values are measured, not assumed)."""

    generated_at: str
    source: str
    classes: list[dict]
    summary: ManifestSummary
    suspicious_duplicate_pairs: list[SuspiciousDuplicatePair]


class QualityResponse(BaseModel):
    generated_at: str
    thresholds: dict
    near_duplicate_method: str | None
    summary: QualitySummary
    flagged_records: list[QualityRecord]


class ScanResponse(BaseModel):
    success: bool = True
    duration_seconds: float
    image_count: int
    summary: ManifestSummary
    quality_summary: QualitySummary
    outputs: dict[str, str]


class ThumbnailQuery(BaseModel):
    size: int = Field(default=256, ge=32, le=1024)
