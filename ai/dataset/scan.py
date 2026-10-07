"""Scan orchestration: discovery -> duplicates -> quality -> persisted outputs.

Single streaming pass over the raw dataset: each image is decoded exactly
once, measurements are kept as small floats, and pixel buffers are released
immediately so the scan scales to much larger datasets.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ai.dataset.discovery import build_record, iter_candidate_files, utc_now_iso
from ai.dataset.duplicates import assign_exact_duplicates, find_suspicious_pairs, perceptual_hash
from ai.dataset.manifest import (
    MANIFEST_CSV_NAME,
    MANIFEST_JSON_NAME,
    QUALITY_CSV_NAME,
    QUALITY_JSON_NAME,
    build_discovery_report,
    build_quality_report,
    save_manifest,
    save_quality_report,
)
from ai.dataset.models import DiscoveryReport, QualityReport
from ai.dataset.quality import (
    RawQualityMetrics,
    build_quality_summary,
    finalize_quality,
    measure_quality,
    thresholds_payload,
)
from ai.dataset.settings import ClassDef, DuplicateSettings, QualitySettings


@dataclass
class ScanResult:
    """Artifacts produced by one scan run."""

    manifest: DiscoveryReport
    quality: QualityReport
    duration_seconds: float
    manifest_json_path: Path
    manifest_csv_path: Path
    quality_json_path: Path
    quality_csv_path: Path


def run_scan(
    raw_dir: Path,
    classes: Sequence[ClassDef],
    quality_settings: QualitySettings,
    duplicate_settings: DuplicateSettings,
    manifests_dir: Path,
    reports_dir: Path,
) -> ScanResult:
    """Run discovery + quality analysis and write all generated outputs.

    The raw directory is only ever opened for reading.
    """
    started = time.perf_counter()

    files = iter_candidate_files(raw_dir)
    records = []
    measurement_map: dict[str, RawQualityMetrics] = {}

    for path in files:
        record, gray = build_record(path, raw_dir, classes)
        records.append(record)
        if gray is not None:
            record.perceptual_hash = perceptual_hash(gray)
            measurement_map[record.image_id] = measure_quality(gray, record)
        # gray goes out of scope here: pixel data is not retained.

    assign_exact_duplicates(records)
    suspicious_pairs = find_suspicious_pairs(records, duplicate_settings.near_duplicate)

    quality_records = [
        finalize_quality(record, measurement_map.get(record.image_id), quality_settings)
        for record in records
    ]

    generated_at = utc_now_iso()
    manifest_report = build_discovery_report(
        records=records,
        suspicious_pairs=suspicious_pairs,
        source=str(raw_dir),
        classes=[{"id": c.id, "name": c.name} for c in classes],
        generated_at=generated_at,
    )
    quality_summary = build_quality_summary(quality_records, quality_settings)
    quality_report = build_quality_report(
        quality_records,
        quality_summary,
        thresholds_payload(quality_settings),
        generated_at,
        duplicate_settings.near_duplicate.method
        if duplicate_settings.near_duplicate.enabled
        else None,
    )

    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    manifest_json = manifests_dir / MANIFEST_JSON_NAME
    manifest_csv = manifests_dir / MANIFEST_CSV_NAME
    quality_json = reports_dir / QUALITY_JSON_NAME
    quality_csv = reports_dir / QUALITY_CSV_NAME

    save_manifest(manifest_report, manifest_json, manifest_csv)
    save_quality_report(quality_report, quality_json, quality_csv)

    return ScanResult(
        manifest=manifest_report,
        quality=quality_report,
        duration_seconds=round(time.perf_counter() - started, 3),
        manifest_json_path=manifest_json,
        manifest_csv_path=manifest_csv,
        quality_json_path=quality_json,
        quality_csv_path=quality_csv,
    )
