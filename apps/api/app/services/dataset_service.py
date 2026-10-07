"""Dataset Stage 2 services: scan orchestration and read-only queries.

All filesystem access goes through the configured paths (raw data is read
only; outputs are written inside the repository data directories). Client
input never becomes a filesystem path.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

from ai.dataset.discovery import decode_image, utc_now_iso
from ai.dataset.manifest import (
    MANIFEST_CSV_NAME,
    MANIFEST_JSON_NAME,
    QUALITY_CSV_NAME,
    QUALITY_JSON_NAME,
    build_quality_report,
    load_manifest,
    load_quality_report,
    save_quality_report,
)
from ai.dataset.models import DiscoveryReport, ManifestRecord, QualityRecord, QualityReport
from ai.dataset.quality import (
    RawQualityMetrics,
    build_quality_summary,
    finalize_quality,
    measure_quality,
    thresholds_payload,
)
from ai.dataset.scan import ScanResult, run_scan
from app.core.config import get_settings, project_root
from app.core.logging import get_logger
from app.core.paths import is_raw_path, raw_data_dir

logger = get_logger("dataset")

IMAGE_ID_PATTERN = re.compile(r"^img_[0-9a-f]{64}$")
DEFAULT_THUMBNAIL_SIZE = 256
MIN_THUMBNAIL_SIZE = 32
MAX_THUMBNAIL_SIZE = 1024


class NotScannedError(RuntimeError):
    """Raised when dataset outputs do not exist yet."""


class ImageNotFoundError(LookupError):
    """Raised when an image_id is unknown."""


class InvalidQueryError(ValueError):
    """Raised when a query parameter value is not allowed."""


def _manifest_json_path() -> Path:
    return project_root() / get_settings().paths.manifests_dir / MANIFEST_JSON_NAME


def _quality_json_path() -> Path:
    return project_root() / get_settings().paths.reports_dir / QUALITY_JSON_NAME


def dataset_output_paths() -> dict[str, str]:
    settings = get_settings()
    root = project_root()
    return {
        "manifest_json": str(
            (root / settings.paths.manifests_dir / MANIFEST_JSON_NAME).relative_to(root)
        ),
        "manifest_csv": str(
            (root / settings.paths.manifests_dir / MANIFEST_CSV_NAME).relative_to(root)
        ),
        "quality_json": str(
            (root / settings.paths.reports_dir / QUALITY_JSON_NAME).relative_to(root)
        ),
        "quality_csv": str(
            (root / settings.paths.reports_dir / QUALITY_CSV_NAME).relative_to(root)
        ),
    }


def manifest_exists() -> bool:
    return _manifest_json_path().is_file()


def load_manifest_or_raise() -> DiscoveryReport:
    path = _manifest_json_path()
    if not path.is_file():
        raise NotScannedError(
            "Dataset not scanned yet. POST /api/dataset/scan or run `python -m cvplatform scan`."
        )
    return load_manifest(path)


def load_quality_or_raise() -> QualityReport:
    path = _quality_json_path()
    if not path.is_file():
        raise NotScannedError(
            "No quality analysis available. POST /api/dataset/scan or run "
            "`python -m cvplatform scan`."
        )
    return load_quality_report(path)


def run_dataset_scan() -> ScanResult:
    """Run the real discovery + quality engine using configured paths only."""
    settings = get_settings()
    raw_dir = raw_data_dir()
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"configured raw dataset directory not found: {raw_dir}")

    result = run_scan(
        raw_dir=raw_dir,
        classes=settings.class_defs(),
        quality_settings=settings.quality,
        duplicate_settings=settings.duplicates,
        manifests_dir=project_root() / settings.paths.manifests_dir,
        reports_dir=project_root() / settings.paths.reports_dir,
    )
    logger.info(
        "dataset scan finished | images=%d | duration=%.3fs",
        result.manifest.record_count,
        result.duration_seconds,
    )
    return result


def rerun_quality_only() -> QualityReport:
    """Recompute quality metrics from an existing manifest (read-only on raw data)."""
    settings = get_settings()
    manifest = load_manifest_or_raise()
    quality_records: list[QualityRecord] = []

    for record in manifest.records:
        metrics: RawQualityMetrics | None = None
        if record.readable:
            decoded = decode_image(Path(record.source_path))
            if decoded.gray is not None:
                metrics = measure_quality(decoded.gray, record)
        quality_records.append(finalize_quality(record, metrics, settings.quality))

    summary = build_quality_summary(quality_records, settings.quality)
    method = (
        settings.duplicates.near_duplicate.method
        if settings.duplicates.near_duplicate.enabled
        else None
    )
    report = build_quality_report(
        quality_records, summary, thresholds_payload(settings.quality), utc_now_iso(), method
    )
    save_quality_report(
        report, _quality_json_path(), _quality_json_path().with_name(QUALITY_CSV_NAME)
    )
    logger.info("quality-only analysis finished | images=%d", len(quality_records))
    return report


def quality_lookup(report: QualityReport | None) -> dict[str, QualityRecord]:
    if report is None:
        return {}
    return {record.image_id: record for record in report.records}


def list_images(
    page: int,
    page_size: int,
    class_name: str | None,
    quality_status: str | None,
) -> dict:
    """Paginated manifest records joined with their quality status."""
    manifest = load_manifest_or_raise()
    quality_by_id = quality_lookup(_load_quality_optional())

    items = []
    for record in manifest.records:
        if class_name and record.class_name != class_name:
            continue
        quality = quality_by_id.get(record.image_id)
        if quality_status and (quality is None or quality.quality_status != quality_status):
            continue
        items.append(_list_item(record, quality))

    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _load_quality_optional() -> QualityReport | None:
    path = _quality_json_path()
    if not path.is_file():
        return None
    return load_quality_report(path)


def _list_item(record: ManifestRecord, quality: QualityRecord | None) -> dict:
    return {
        "image_id": record.image_id,
        "filename": record.filename,
        "source_relative_path": record.source_relative_path,
        "class_name": record.class_name,
        "class_id": record.class_id,
        "width": record.width,
        "height": record.height,
        "channels": record.channels,
        "color_mode": record.color_mode,
        "file_size_bytes": record.file_size_bytes,
        "extension": record.extension,
        "readable": record.readable,
        "status": record.status,
        "is_exact_duplicate": record.is_exact_duplicate,
        "duplicate_group_id": record.duplicate_group_id,
        "is_suspicious_duplicate": record.is_suspicious_duplicate,
        "quality_status": quality.quality_status if quality else None,
        "flags": quality.flags if quality else [],
    }


def get_image_detail(image_id: str) -> dict:
    record = _find_record(image_id)
    quality = quality_lookup(_load_quality_optional()).get(image_id)
    return {"record": record, "quality": quality}


def _find_record(image_id: str) -> ManifestRecord:
    if not IMAGE_ID_PATTERN.match(image_id):
        raise ImageNotFoundError(f"unknown image_id: {image_id}")
    manifest = load_manifest_or_raise()
    for record in manifest.records:
        if record.image_id == image_id:
            return record
    raise ImageNotFoundError(f"unknown image_id: {image_id}")


def image_thumbnail(image_id: str, size: int) -> bytes:
    """Read-only thumbnail generated in memory from the raw source file."""
    record = _find_record(image_id)
    if not record.readable:
        raise ValueError(f"image is not readable: {record.source_relative_path}")

    source = Path(record.source_path)
    # Defense in depth: the path must resolve inside the read-only raw dataset
    # and the file must exist; we only ever open it for reading.
    if not is_raw_path(source) or not source.is_file():
        raise ValueError(f"source path escapes the raw dataset: {record.source_relative_path}")

    clamped = max(MIN_THUMBNAIL_SIZE, min(MAX_THUMBNAIL_SIZE, size))
    with Image.open(source) as img:
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        img.thumbnail((clamped, clamped))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()
