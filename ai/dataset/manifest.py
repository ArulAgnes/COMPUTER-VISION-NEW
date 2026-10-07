"""Manifest persistence: JSON (full fidelity) + CSV (spreadsheet friendly)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from ai.dataset.models import (
    MANIFEST_SCHEMA_VERSION,
    QUALITY_SCHEMA_VERSION,
    DiscoveryReport,
    ManifestRecord,
    ManifestSummary,
    QualityRecord,
    QualityReport,
    QualitySummary,
    SuspiciousDuplicatePair,
)

MANIFEST_JSON_NAME = "dataset_manifest.json"
MANIFEST_CSV_NAME = "dataset_manifest.csv"
QUALITY_JSON_NAME = "quality_report.json"
QUALITY_CSV_NAME = "quality_report.csv"

MANIFEST_CSV_COLUMNS = [
    "image_id",
    "source_relative_path",
    "class_name",
    "class_id",
    "filename",
    "extension",
    "width",
    "height",
    "channels",
    "color_mode",
    "file_size_bytes",
    "sha256",
    "perceptual_hash",
    "readable",
    "decode_error",
    "status",
    "is_exact_duplicate",
    "duplicate_group_id",
    "is_suspicious_duplicate",
    "discovery_timestamp",
]

QUALITY_CSV_COLUMNS = [
    "image_id",
    "source_relative_path",
    "class_name",
    "quality_status",
    "flags",
    "width",
    "height",
    "pixel_count",
    "min_dimension",
    "aspect_ratio",
    "blur_score",
    "brightness_mean",
    "brightness_std",
    "brightness_min",
    "brightness_max",
    "color_mode",
    "channels",
    "file_size_bytes",
    "file_size_kb",
    "file_size_mb",
    "sha256",
    "is_exact_duplicate",
    "duplicate_group_id",
    "is_suspicious_duplicate",
]


def build_manifest_summary(
    records: Sequence[ManifestRecord], suspicious_pairs: Sequence[SuspiciousDuplicatePair]
) -> ManifestSummary:
    """Aggregate real discovery statistics (all values derived from records)."""
    class_counts: dict[str, int] = {}
    format_counts: dict[str, int] = {}
    dimension_counts: dict[str, int] = {}
    grayscale = color = 0

    for record in records:
        if record.class_id is not None and record.class_name is not None:
            class_counts[record.class_name] = class_counts.get(record.class_name, 0) + 1
        format_counts[record.extension] = format_counts.get(record.extension, 0) + 1
        if record.width and record.height:
            key = f"{record.width}x{record.height}"
            dimension_counts[key] = dimension_counts.get(key, 0) + 1
        if record.color_mode in ("L", "1", "LA"):
            grayscale += 1
        else:
            color += 1

    exact_groups = {r.duplicate_group_id for r in records if r.is_exact_duplicate}
    suspicious_ids = {p.image_id_a for p in suspicious_pairs} | {
        p.image_id_b for p in suspicious_pairs
    }

    return ManifestSummary(
        total_images=len(records),
        readable=sum(1 for r in records if r.readable),
        unreadable=sum(1 for r in records if not r.readable),
        class_counts=dict(sorted(class_counts.items())),
        unknown_class=sum(1 for r in records if r.status == "unknown_class"),
        no_class=sum(1 for r in records if r.status == "no_class"),
        format_counts=dict(sorted(format_counts.items())),
        dimension_counts=dict(sorted(dimension_counts.items())),
        exact_duplicate_images=sum(1 for r in records if r.is_exact_duplicate),
        exact_duplicate_groups=len(exact_groups),
        suspicious_duplicate_images=len(suspicious_ids),
        suspicious_duplicate_pairs=len(suspicious_pairs),
        grayscale_images=grayscale,
        color_images=color,
        total_bytes=sum(r.file_size_bytes for r in records),
    )


def build_discovery_report(
    records: list[ManifestRecord],
    suspicious_pairs: list[SuspiciousDuplicatePair],
    source: str,
    classes: Sequence[dict],
    generated_at: str,
) -> DiscoveryReport:
    return DiscoveryReport(
        schema_version=MANIFEST_SCHEMA_VERSION,
        generated_at=generated_at,
        source=source,
        classes=list(classes),
        record_count=len(records),
        summary=build_manifest_summary(records, suspicious_pairs),
        suspicious_duplicate_pairs=suspicious_pairs,
        records=records,
    )


def build_quality_report(
    quality_records: list[QualityRecord],
    summary: QualitySummary,
    thresholds: dict,
    generated_at: str,
    near_duplicate_method: str | None,
) -> QualityReport:
    flagged = [r for r in quality_records if r.quality_status in ("REVIEW", "FAIL")]
    return QualityReport(
        schema_version=QUALITY_SCHEMA_VERSION,
        generated_at=generated_at,
        thresholds=thresholds,
        near_duplicate_method=near_duplicate_method,
        summary=summary,
        flagged_records=flagged,
        records=quality_records,
    )


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def save_manifest(report: DiscoveryReport, json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    rows = [r.model_dump() for r in report.records]
    _write_csv(csv_path, MANIFEST_CSV_COLUMNS, rows)


def load_manifest(json_path: Path) -> DiscoveryReport:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return DiscoveryReport.model_validate(data)


def save_quality_report(report: QualityReport, json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    rows = [r.model_dump() for r in report.records]
    _write_csv(csv_path, QUALITY_CSV_COLUMNS, rows)


def load_quality_report(json_path: Path) -> QualityReport:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return QualityReport.model_validate(data)
