"""Full scan tests: outputs, reproducibility, raw-data invariance, bad files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai.dataset.discovery import iter_candidate_files
from ai.dataset.manifest import (
    load_manifest,
    load_quality_report,
)
from ai.dataset.scan import run_scan


def sha_map(raw_dir: Path) -> dict[str, str]:
    return {
        p.relative_to(raw_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in iter_candidate_files(raw_dir)
    }


def scan_to(raw_dir: Path, settings, out: Path):
    return run_scan(
        raw_dir=raw_dir,
        classes=settings.class_defs(),
        quality_settings=settings.quality,
        duplicate_settings=settings.duplicates,
        manifests_dir=out / "manifests",
        reports_dir=out / "reports",
    )


def strip_timestamps(payload: dict) -> dict:
    """Remove wall-clock fields so two runs can be compared byte-for-byte."""
    payload = json.loads(json.dumps(payload))
    payload.pop("generated_at", None)
    for record in payload.get("records", []):
        record.pop("discovery_timestamp", None)
    return payload


def test_scan_writes_all_outputs(raw_dir: Path, settings, tmp_path: Path) -> None:
    before = sha_map(raw_dir)
    result = scan_to(raw_dir, settings, tmp_path)

    for path in (
        result.manifest_json_path,
        result.manifest_csv_path,
        result.quality_json_path,
        result.quality_csv_path,
    ):
        assert path.is_file(), f"missing output: {path}"

    manifest = load_manifest(result.manifest_json_path)
    quality = load_quality_report(result.quality_json_path)
    assert manifest.record_count == quality.summary.total
    assert [r.image_id for r in manifest.records] == [r.image_id for r in quality.records]

    assert sha_map(raw_dir) == before, "scan must not modify the raw dataset"


def test_scan_is_reproducible(raw_dir: Path, settings, tmp_path: Path) -> None:
    first = scan_to(raw_dir, settings, tmp_path / "run1")
    second = scan_to(raw_dir, settings, tmp_path / "run2")

    manifest1 = json.loads(first.manifest_json_path.read_text(encoding="utf-8"))
    manifest2 = json.loads(second.manifest_json_path.read_text(encoding="utf-8"))
    assert strip_timestamps(manifest1) == strip_timestamps(manifest2)

    quality1 = json.loads(first.quality_json_path.read_text(encoding="utf-8"))
    quality2 = json.loads(second.quality_json_path.read_text(encoding="utf-8"))
    assert strip_timestamps(quality1) == strip_timestamps(quality2)


def test_scan_summary_matches_stage0(
    raw_dir: Path, settings, tmp_path: Path, stage0_baseline: dict
) -> None:
    result = scan_to(raw_dir, settings, tmp_path)
    summary = result.manifest.summary

    assert summary.total_images == stage0_baseline["total_images"]
    assert summary.class_counts == stage0_baseline["class_counts"]
    assert summary.format_counts == stage0_baseline["formats"]
    assert summary.unreadable == stage0_baseline["unreadable_files"]
    assert summary.exact_duplicate_groups == stage0_baseline["exact_duplicate_groups"]
    assert summary.suspicious_duplicate_pairs == stage0_baseline["suspicious_duplicate_pairs"]

    quality = result.quality.summary
    assert quality.total == summary.total_images
    assert quality.pass_count + quality.review_count + quality.fail_count == quality.total


def test_scan_computes_real_thresholds(raw_dir: Path, settings, tmp_path: Path) -> None:
    result = scan_to(raw_dir, settings, tmp_path)
    thresholds = result.quality.thresholds
    assert thresholds["blur_review_threshold"] == settings.quality.blur.review_threshold
    assert thresholds["blur_fail_threshold"] == settings.quality.blur.fail_threshold
    assert thresholds["min_width"] == settings.quality.min_width


def test_scan_tolerates_corrupted_image(tmp_path: Path, settings, raw_dir: Path) -> None:
    """A corrupt file is reported (unreadable + FAIL), never aborts the scan."""
    dataset = tmp_path / "raw"
    (dataset / "bell").mkdir(parents=True)
    good = next(p for p in (raw_dir / "bell").iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    (dataset / "bell" / "good.jpg").write_bytes(good.read_bytes())
    (dataset / "bell" / "corrupt.jpg").write_bytes(b"this is not a jpeg \x00\x01\x02")

    result = scan_to(dataset, settings, tmp_path / "out")

    assert result.manifest.record_count == 2
    assert result.manifest.summary.unreadable == 1
    broken = next(r for r in result.manifest.records if not r.readable)
    assert broken.status == "unreadable"
    assert broken.decode_error

    quality = next(q for q in result.quality.records if q.image_id == broken.image_id)
    assert quality.quality_status == "FAIL"
    assert "decode_failed" in quality.flags
    assert quality.blur_score is None


def test_scan_reports_duplicate_and_unknown_class(tmp_path: Path, settings, raw_dir: Path) -> None:
    dataset = tmp_path / "raw"
    (dataset / "bell").mkdir(parents=True)
    (dataset / "not_a_class").mkdir()
    sources = [
        p for p in sorted((raw_dir / "bell").iterdir()) if p.suffix.lower() in (".jpg", ".jpeg")
    ]
    good, other = sources[0], sources[1]
    (dataset / "bell" / "one.jpg").write_bytes(good.read_bytes())
    (dataset / "bell" / "two.jpg").write_bytes(good.read_bytes())  # exact duplicate content
    (dataset / "not_a_class" / "stranger.jpg").write_bytes(other.read_bytes())

    result = scan_to(dataset, settings, tmp_path / "out")
    summary = result.manifest.summary

    assert summary.exact_duplicate_images == 2
    assert summary.exact_duplicate_groups == 1
    assert summary.unknown_class == 1

    by_name = {r.filename: r for r in result.manifest.records}
    assert by_name["one.jpg"].is_exact_duplicate and by_name["two.jpg"].is_exact_duplicate
    assert by_name["one.jpg"].duplicate_group_id == by_name["two.jpg"].duplicate_group_id
    assert by_name["stranger.jpg"].status == "unknown_class"
