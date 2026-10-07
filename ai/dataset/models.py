"""Data models for dataset manifests and quality reports."""

from __future__ import annotations

from pydantic import BaseModel, Field

MANIFEST_SCHEMA_VERSION = 1
QUALITY_SCHEMA_VERSION = 1

VALID = "valid"
UNREADABLE = "unreadable"
UNKNOWN_CLASS = "unknown_class"
NO_CLASS = "no_class"

PASS = "PASS"
REVIEW = "REVIEW"
FAIL = "FAIL"


class ManifestRecord(BaseModel):
    """One discovered source image. ``image_id`` is deterministic:

    ``img_`` + sha256(source_relative_path + NUL + content_sha256), so the same
    source file always receives the same id, while exact duplicates in
    different folders stay separately addressable.
    """

    image_id: str
    source_path: str
    source_relative_path: str
    class_name: str | None
    class_id: int | None
    filename: str
    extension: str
    width: int | None = None
    height: int | None = None
    channels: int | None = None
    color_mode: str | None = None
    file_size_bytes: int
    sha256: str
    perceptual_hash: str | None = None
    readable: bool
    decode_error: str | None = None
    status: str
    is_exact_duplicate: bool = False
    duplicate_group_id: str | None = None
    is_suspicious_duplicate: bool = False
    discovery_timestamp: str


class QualityRecord(BaseModel):
    """Measured quality metrics for one image (None when unreadable)."""

    image_id: str
    source_relative_path: str
    class_name: str | None
    quality_status: str
    flags: list[str]
    width: int | None = None
    height: int | None = None
    pixel_count: int | None = None
    min_dimension: int | None = None
    aspect_ratio: float | None = None
    blur_score: float | None = None
    brightness_mean: float | None = None
    brightness_std: float | None = None
    brightness_min: float | None = None
    brightness_max: float | None = None
    color_mode: str | None = None
    channels: int | None = None
    file_size_bytes: int
    file_size_kb: float
    file_size_mb: float
    sha256: str
    is_exact_duplicate: bool
    duplicate_group_id: str | None = None
    is_suspicious_duplicate: bool


class SuspiciousDuplicatePair(BaseModel):
    """A near-duplicate pair found by perceptual hashing."""

    image_id_a: str
    image_id_b: str
    path_a: str
    path_b: str
    hamming_distance: int
    method: str


class ManifestSummary(BaseModel):
    """Real counts derived from the scan (never hardcoded)."""

    total_images: int
    readable: int
    unreadable: int
    class_counts: dict[str, int]
    unknown_class: int = 0
    no_class: int = 0
    format_counts: dict[str, int]
    dimension_counts: dict[str, int]
    exact_duplicate_images: int
    exact_duplicate_groups: int
    suspicious_duplicate_images: int
    suspicious_duplicate_pairs: int
    grayscale_images: int
    color_images: int
    total_bytes: int


class QualitySummary(BaseModel):
    """Real quality counts and distributions."""

    total: int
    pass_count: int
    review_count: int
    fail_count: int
    flagged_count: int
    flag_counts: dict[str, int]
    blur_statistics: dict[str, float | None]
    brightness_statistics: dict[str, float | None]
    blur_distribution: dict[str, int]
    brightness_distribution: dict[str, int]
    resolution_distribution: dict[str, int]
    low_resolution_count: int
    exact_duplicate_images: int
    suspicious_duplicate_images: int


class DiscoveryReport(BaseModel):
    """data/manifests/dataset_manifest.json"""

    schema_version: int
    generated_at: str
    source: str
    classes: list[dict]
    record_count: int
    summary: ManifestSummary
    suspicious_duplicate_pairs: list[SuspiciousDuplicatePair]
    records: list[ManifestRecord]


class QualityReport(BaseModel):
    """data/reports/quality_report.json"""

    schema_version: int
    generated_at: str
    thresholds: dict
    near_duplicate_method: str | None = None
    summary: QualitySummary
    flagged_records: list[QualityRecord] = Field(default_factory=list)
    records: list[QualityRecord] = Field(default_factory=list)
