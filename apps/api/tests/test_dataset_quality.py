"""Image quality logic tests on synthetic images with known properties.

These verify the *calculations* (Laplacian variance, mean brightness,
aspect ratio) and the configurable flag/status rules — no dataset counts.
"""

from __future__ import annotations

import numpy as np
import pytest

from ai.dataset.models import FAIL, PASS, REVIEW, ManifestRecord
from ai.dataset.quality import (
    FLAG_BLUR_FAIL,
    FLAG_DECODE_FAILED,
    FLAG_EXACT_DUPLICATE,
    FLAG_EXTREME_ASPECT,
    FLAG_LOW_RESOLUTION,
    FLAG_TOO_BRIGHT,
    FLAG_TOO_DARK,
    RawQualityMetrics,
    build_quality_summary,
    derive_status,
    finalize_quality,
    measure_quality,
    thresholds_payload,
)

TIMESTAMP = "2026-10-07T00:00:00+00:00"


def make_record(**overrides) -> ManifestRecord:
    base = dict(
        image_id="img_" + "0" * 64,
        source_path="X:/raw/bell/x.jpg",
        source_relative_path="bell/x.jpg",
        class_name="bell",
        class_id=0,
        filename="x.jpg",
        extension="jpg",
        width=256,
        height=256,
        channels=3,
        color_mode="RGB",
        file_size_bytes=1234,
        sha256="a" * 64,
        readable=True,
        status="valid",
        discovery_timestamp=TIMESTAMP,
    )
    base.update(overrides)
    return ManifestRecord(**base)


@pytest.fixture()
def quality_settings(settings):
    return settings.quality


def test_blur_score_of_uniform_image_is_near_zero(quality_settings) -> None:
    gray = np.full((256, 256), 128, dtype=np.uint8)
    record = make_record()
    metrics = measure_quality(gray, record)
    assert metrics.blur_score is not None
    assert metrics.blur_score < quality_settings.blur.fail_threshold


def test_blur_score_of_noise_is_above_review_threshold(quality_settings) -> None:
    gray = np.random.default_rng(0).integers(0, 256, (256, 256), dtype=np.uint8)
    metrics = measure_quality(gray, make_record())
    assert metrics.blur_score > quality_settings.blur.review_threshold
    assert metrics.brightness_mean is not None
    assert 100 < metrics.brightness_mean < 160


def test_flags_uniform_gray_is_blur_fail(quality_settings) -> None:
    from ai.dataset.quality import compute_flags

    gray = np.full((256, 256), 128, dtype=np.uint8)
    record = make_record()
    metrics = measure_quality(gray, record)
    flags = compute_flags(record, metrics, quality_settings)
    assert flags == [FLAG_BLUR_FAIL]
    assert derive_status(flags, quality_settings) == FAIL


def test_flags_dark_and_bright(quality_settings) -> None:
    from ai.dataset.quality import compute_flags

    rng = np.random.default_rng(1)
    dark = rng.integers(0, 30, (256, 256), dtype=np.uint8)
    dark_flags = compute_flags(
        make_record(), measure_quality(dark, make_record()), quality_settings
    )
    assert FLAG_TOO_DARK in dark_flags

    bright = rng.integers(225, 256, (256, 256), dtype=np.uint8)
    bright_flags = compute_flags(
        make_record(), measure_quality(bright, make_record()), quality_settings
    )
    assert FLAG_TOO_BRIGHT in bright_flags


def test_flags_low_resolution_and_extreme_aspect(quality_settings) -> None:
    from ai.dataset.quality import compute_flags

    small_record = make_record(width=64, height=64)
    small = np.full((64, 64), 128, dtype=np.uint8)
    assert compute_flags(small_record, measure_quality(small, small_record), quality_settings) == [
        FLAG_LOW_RESOLUTION,
        FLAG_BLUR_FAIL,
    ]

    wide_record = make_record(width=800, height=200)
    wide = np.full((200, 800), 128, dtype=np.uint8)
    assert compute_flags(wide_record, measure_quality(wide, wide_record), quality_settings) == [
        FLAG_BLUR_FAIL,
        FLAG_EXTREME_ASPECT,
    ]


def test_unreadable_image_fails_with_decode_flag(quality_settings) -> None:
    record = make_record(
        readable=False, status="unreadable", decode_error="broken", width=None, height=None
    )
    quality = finalize_quality(record, None, quality_settings)
    assert quality.flags == [FLAG_DECODE_FAILED]
    assert quality.quality_status == FAIL
    assert quality.blur_score is None
    assert quality.brightness_mean is None


def test_exact_duplicate_maps_to_review(quality_settings) -> None:
    record = make_record(is_exact_duplicate=True, duplicate_group_id="dup_" + "b" * 12)
    quality = finalize_quality(record, _sharp_metrics(), quality_settings)
    assert FLAG_EXACT_DUPLICATE in quality.flags
    assert quality.quality_status == REVIEW  # duplicate is review, not fail


def _sharp_metrics() -> RawQualityMetrics:
    gray = np.full((256, 256), 128, dtype=np.uint8)
    gray[::8] = 0  # give the Laplacian something to respond to
    return measure_quality(gray, make_record())


def test_derive_status_precedence(quality_settings) -> None:
    assert derive_status([], quality_settings) == PASS
    assert derive_status([FLAG_TOO_DARK], quality_settings) == REVIEW
    assert derive_status([FLAG_TOO_DARK, FLAG_BLUR_FAIL], quality_settings) == FAIL
    assert derive_status([FLAG_EXACT_DUPLICATE], quality_settings) == REVIEW


def test_finalize_quality_derives_size_fields(quality_settings) -> None:
    record = make_record(file_size_bytes=2 * 1024 * 1024 + 512)
    quality = finalize_quality(record, _sharp_metrics(), quality_settings)
    assert quality.file_size_kb == 2048.5
    assert quality.file_size_mb == 2.0
    assert quality.pixel_count == 256 * 256
    assert quality.min_dimension == 256
    assert quality.aspect_ratio == 1.0


def test_quality_summary_is_internally_consistent(quality_settings) -> None:
    sharp = finalize_quality(make_record(), _sharp_metrics(), quality_settings)
    flat_record = make_record(image_id="img_" + "1" * 64, sha256="c" * 64)
    flat = finalize_quality(
        flat_record,
        measure_quality(np.full((256, 256), 128, dtype=np.uint8), flat_record),
        quality_settings,
    )
    broken = finalize_quality(
        make_record(
            image_id="img_" + "2" * 64, sha256="d" * 64, readable=False, status="unreadable"
        ),
        None,
        quality_settings,
    )

    summary = build_quality_summary([sharp, flat, broken], quality_settings)
    assert summary.total == 3
    assert summary.pass_count + summary.review_count + summary.fail_count == 3
    assert summary.fail_count == 2  # flat (blur) + broken (decode)
    assert summary.flagged_count == summary.review_count + summary.fail_count
    assert sum(summary.blur_distribution.values()) == 3
    assert sum(summary.brightness_distribution.values()) == 3
    assert summary.flag_counts[FLAG_BLUR_FAIL] == 1
    assert summary.flag_counts[FLAG_DECODE_FAILED] == 1


def test_thresholds_payload_reports_configured_values(quality_settings) -> None:
    payload = thresholds_payload(quality_settings)
    assert payload["blur_review_threshold"] == quality_settings.blur.review_threshold
    assert payload["blur_fail_threshold"] == quality_settings.blur.fail_threshold
    assert payload["brightness_dark_threshold"] == quality_settings.brightness.dark_threshold
    assert payload["fail_flags"] == quality_settings.status_rules.fail_flags
    assert payload["note"].startswith("Configurable heuristics")
