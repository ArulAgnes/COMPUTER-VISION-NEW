"""Duplicate detection.

Exact duplicates: identical SHA-256 content hash.
Suspicious (near) duplicates: 64-bit difference hash (dHash) Hamming distance
— a real calculation, never a guess. Method and threshold are configurable.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Sequence

import cv2
import numpy as np

from ai.dataset.models import ManifestRecord, SuspiciousDuplicatePair
from ai.dataset.settings import NearDuplicateSettings

EXACT_GROUP_PREFIX = "dup_"


def perceptual_hash(gray: np.ndarray) -> str:
    """64-bit difference hash: resize to 9x8 grayscale, compare horizontal neighbours."""
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = small[:, 1:] > small[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hamming_distance(a_hex: str, b_hex: str) -> int:
    return (int(a_hex, 16) ^ int(b_hex, 16)).bit_count()


def assign_exact_duplicates(records: Sequence[ManifestRecord]) -> int:
    """Flag records sharing a SHA-256 hash. Returns the number of duplicate groups."""
    by_hash: dict[str, list[ManifestRecord]] = defaultdict(list)
    for record in records:
        by_hash[record.sha256].append(record)

    groups = 0
    for sha256, members in by_hash.items():
        if len(members) > 1:
            groups += 1
            group_id = EXACT_GROUP_PREFIX + sha256[:12]
            for member in members:
                member.is_exact_duplicate = True
                member.duplicate_group_id = group_id
    return groups


def find_suspicious_pairs(
    records: Sequence[ManifestRecord], settings: NearDuplicateSettings
) -> list[SuspiciousDuplicatePair]:
    """Pairwise near-duplicate detection among readable, non-identical images.

    Exact duplicates (same SHA-256) are excluded — they are already reported
    by exact detection. O(n^2) over perceptual hashes; acceptable for the
    current dataset and documented as a future optimization for very large sets.
    """
    if not settings.enabled:
        return []

    pairs: list[SuspiciousDuplicatePair] = []
    hashed = [r for r in records if r.perceptual_hash and r.readable]
    for a, b in combinations(hashed, 2):
        if a.sha256 == b.sha256:
            continue
        distance = hamming_distance(a.perceptual_hash or "", b.perceptual_hash or "")
        if distance <= settings.max_hamming_distance:
            a.is_suspicious_duplicate = True
            b.is_suspicious_duplicate = True
            pairs.append(
                SuspiciousDuplicatePair(
                    image_id_a=a.image_id,
                    image_id_b=b.image_id,
                    path_a=a.source_relative_path,
                    path_b=b.source_relative_path,
                    hamming_distance=distance,
                    method=settings.method,
                )
            )
    return pairs
