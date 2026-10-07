"""Dataset discovery + image quality endpoints (Stage 2).

All values returned here are real measurements produced by the ``ai``
engine: nothing is mocked, sampled or hardcoded.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.schemas.dataset import (
    DatasetSummaryResponse,
    ImageDetailResponse,
    ImageListResponse,
    QualityResponse,
    ScanResponse,
)
from app.services import dataset_service
from app.services.dataset_service import InvalidQueryError

router = APIRouter()

QUALITY_STATUSES = ("PASS", "REVIEW", "FAIL")


@router.get("/api/dataset/summary", response_model=DatasetSummaryResponse, tags=["dataset"])
def dataset_summary() -> DatasetSummaryResponse:
    """Discovery summary (counts are measured during the last scan)."""
    manifest = dataset_service.load_manifest_or_raise()
    return DatasetSummaryResponse(
        generated_at=manifest.generated_at,
        source=manifest.source,
        classes=manifest.classes,
        summary=manifest.summary,
        suspicious_duplicate_pairs=manifest.suspicious_duplicate_pairs,
    )


@router.get("/api/dataset/images", response_model=ImageListResponse, tags=["dataset"])
def list_dataset_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=200),
    class_name: str | None = Query(None),
    quality_status: str | None = Query(None),
) -> ImageListResponse:
    """Paginated image list with class and quality-status filters."""
    if quality_status is not None and quality_status not in QUALITY_STATUSES:
        raise InvalidQueryError(f"quality_status must be one of {', '.join(QUALITY_STATUSES)}")
    page_data = dataset_service.list_images(page, page_size, class_name, quality_status)
    return ImageListResponse(**page_data)


@router.get(
    "/api/dataset/images/{image_id}",
    response_model=ImageDetailResponse,
    tags=["dataset"],
)
def get_dataset_image(image_id: str) -> ImageDetailResponse:
    """Full manifest record + quality analysis for one image."""
    detail = dataset_service.get_image_detail(image_id)
    record = detail["record"]
    detail["record"] = record.model_dump(exclude={"source_path"})
    return ImageDetailResponse(**detail)


@router.get("/api/dataset/images/{image_id}/thumbnail", tags=["dataset"])
def get_dataset_thumbnail(
    image_id: str,
    size: int = Query(256, ge=32, le=1024),
) -> Response:
    """JPEG thumbnail generated in memory from the read-only source file."""
    payload = dataset_service.image_thumbnail(image_id, size)
    return Response(
        content=payload,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/api/dataset/quality", response_model=QualityResponse, tags=["dataset"])
def dataset_quality() -> QualityResponse:
    """Quality report: summary, flagged images and the thresholds applied."""
    report = dataset_service.load_quality_or_raise()
    return QualityResponse(
        generated_at=report.generated_at,
        thresholds=report.thresholds,
        near_duplicate_method=report.near_duplicate_method,
        summary=report.summary,
        flagged_records=report.flagged_records,
    )


@router.post("/api/dataset/scan", response_model=ScanResponse, tags=["dataset"])
def scan_dataset() -> ScanResponse:
    """Run discovery + quality analysis over the raw dataset (read-only).

    Writes the manifest and quality report inside the repository; the raw
    dataset is never modified. Exit code semantics live in the CLI.
    """
    result = dataset_service.run_dataset_scan()
    return ScanResponse(
        duration_seconds=result.duration_seconds,
        image_count=result.manifest.record_count,
        summary=result.manifest.summary,
        quality_summary=result.quality.summary,
        outputs=dataset_service.dataset_output_paths(),
    )
