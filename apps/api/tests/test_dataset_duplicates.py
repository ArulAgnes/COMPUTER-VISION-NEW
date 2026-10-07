"""Duplicate detection tests: exact (SHA-256) and suspicious (dHash) pairs."""

from __future__ import annotations

import hashlib

import numpy as np

from ai.dataset.discovery import make_image_id
from ai.dataset.duplicates import (
    EXACT_GROUP_PREFIX,
    assign_exact_duplicates,
    find_suspicious_pairs,
    hamming_distance,
    perceptual_hash,
)
from ai.dataset.models import ManifestRecord
from ai.dataset.settings import NearDuplicateSettings

TIMESTAMP = "2026-10-07T00:00:00+00:00"


def make_record(relative: str, content: bytes, **overrides) -> ManifestRecord:
    sha256 = hashlib.sha256(content).hexdigest()
    base = dict(
        image_id=make_image_id(relative, sha256),
        source_path="X:/raw/" + relative,
        source_relative_path=relative,
        class_name="bell",
        class_id=0,
        filename=relative.split("/")[-1],
        extension="jpg",
        width=64,
        height=64,
        channels=3,
        color_mode="RGB",
        file_size_bytes=len(content),
        sha256=sha256,
        readable=True,
        status="valid",
        discovery_timestamp=TIMESTAMP,
    )
    base.update(overrides)
    return ManifestRecord(**base)


def near_settings(max_distance: int = 6) -> NearDuplicateSettings:
    return NearDuplicateSettings(
        enabled=True, method="dhash_hamming", max_hamming_distance=max_distance
    )


def test_hamming_distance_counts_flipped_bits() -> None:
    assert hamming_distance("0" * 16, "0" * 16) == 0
    assert hamming_distance("0" * 16, "f" * 16) == 64
    assert hamming_distance("0000000000000000", "0000000000000001") == 1


def test_perceptual_hash_is_deterministic_and_64_bit() -> None:
    gray = np.random.default_rng(7).integers(0, 256, (64, 64), dtype=np.uint8)
    a = perceptual_hash(gray)
    b = perceptual_hash(gray.copy())
    assert a == b
    assert len(a) == 16
    int(a, 16)  # valid hex


def test_exact_duplicates_grouped_by_content() -> None:
    content = b"identical-bytes"
    a = make_record("bell/a.jpg", content)
    b = make_record("oillamp/b.jpg", content)
    c = make_record("bell/c.jpg", b"different-bytes")

    groups = assign_exact_duplicates([a, b, c])

    assert groups == 1
    assert a.is_exact_duplicate and b.is_exact_duplicate
    assert a.duplicate_group_id == b.duplicate_group_id
    assert a.duplicate_group_id.startswith(EXACT_GROUP_PREFIX)
    assert not c.is_exact_duplicate
    assert c.duplicate_group_id is None


def test_unique_contents_produce_no_exact_groups() -> None:
    records = [make_record(f"bell/{i}.jpg", bytes([i]) * 8) for i in range(3)]
    assert assign_exact_duplicates(records) == 0
    assert all(not r.is_exact_duplicate for r in records)


def test_suspicious_pairs_detected_for_near_identical_images() -> None:
    base = np.random.default_rng(3).integers(0, 256, (64, 64), dtype=np.uint8)
    perturbed = base.copy()
    perturbed[10:13, 10:13] = np.clip(perturbed[10:13, 10:13].astype(np.int16) + 4, 0, 255).astype(
        np.uint8
    )

    a = make_record("bell/a.jpg", b"version-a")
    a.perceptual_hash = perceptual_hash(base)
    b = make_record("oillamp/b.jpg", b"version-b")
    b.perceptual_hash = perceptual_hash(perturbed)

    pairs = find_suspicious_pairs([a, b], near_settings(max_distance=8))

    assert len(pairs) == 1
    assert pairs[0].hamming_distance == hamming_distance(a.perceptual_hash, b.perceptual_hash)
    assert pairs[0].hamming_distance <= 8
    assert a.is_suspicious_duplicate and b.is_suspicious_duplicate


def test_identical_images_excluded_from_suspicious_pairs() -> None:
    content = b"same-content"
    a = make_record("bell/a.jpg", content)
    a.perceptual_hash = "0123456789abcdef"
    b = make_record("oillamp/b.jpg", content)
    b.perceptual_hash = "0123456789abcdef"

    pairs = find_suspicious_pairs([a, b], near_settings(max_distance=6))

    assert pairs == []
    assert not a.is_suspicious_duplicate


def test_dissimilar_images_not_flagged() -> None:
    left = np.zeros((64, 64), dtype=np.uint8)
    left[:, 32:] = 255  # vertical step
    right = np.zeros((64, 64), dtype=np.uint8)
    right[32:, :] = 255  # horizontal step

    a = make_record("bell/a.jpg", b"a")
    a.perceptual_hash = perceptual_hash(left)
    b = make_record("bell/b.jpg", b"b")
    b.perceptual_hash = perceptual_hash(right)

    pairs = find_suspicious_pairs([a, b], near_settings(max_distance=6))

    assert pairs == []
    assert not a.is_suspicious_duplicate and not b.is_suspicious_duplicate


def test_near_duplicate_detection_can_be_disabled() -> None:
    base = np.random.default_rng(5).integers(0, 256, (64, 64), dtype=np.uint8)
    a = make_record("bell/a.jpg", b"a")
    a.perceptual_hash = perceptual_hash(base)
    b = make_record("bell/b.jpg", b"b")
    b.perceptual_hash = perceptual_hash(base.copy())

    disabled = NearDuplicateSettings(enabled=False, method="dhash_hamming", max_hamming_distance=6)
    assert find_suspicious_pairs([a, b], disabled) == []
    assert not a.is_suspicious_duplicate


def test_unreadable_records_excluded_from_near_duplicates() -> None:
    a = make_record("bell/a.jpg", b"a", readable=False, status="unreadable", perceptual_hash=None)
    b = make_record("bell/b.jpg", b"b")
    b.perceptual_hash = "0" * 16

    assert find_suspicious_pairs([a, b], near_settings()) == []
