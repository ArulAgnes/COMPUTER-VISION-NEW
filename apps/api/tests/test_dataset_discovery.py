"""Discovery tests against the real read-only raw dataset (Stage 2).

The raw dataset is only ever opened for reading; these tests compare the
engine's measured output against the Stage 0 baseline file — no counts are
hardcoded in the test code.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ai.dataset.discovery import build_record, iter_candidate_files, make_image_id

IMAGE_ID_RE = re.compile(r"^img_[0-9a-f]{64}$")


def _sha256_map(raw_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(raw_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in iter_candidate_files(raw_dir)
    }


def test_raw_sha256_unchanged_by_discovery(raw_dir: Path) -> None:
    before = _sha256_map(raw_dir)
    for path in iter_candidate_files(raw_dir):
        build_record(path, raw_dir, [])
    after = _sha256_map(raw_dir)
    assert before == after, "discovery must never modify raw dataset bytes"


def test_discovered_files_match_stage0(raw_dir: Path, settings, stage0_baseline: dict) -> None:
    candidates = iter_candidate_files(raw_dir)
    assert len(candidates) == stage0_baseline["total_images"]

    records = [build_record(path, raw_dir, settings.class_defs())[0] for path in candidates]
    class_counts: dict[str, int] = {}
    format_counts: dict[str, int] = {}
    for record in records:
        if record.class_name is not None and record.class_id is not None:
            class_counts[record.class_name] = class_counts.get(record.class_name, 0) + 1
        format_counts[record.extension] = format_counts.get(record.extension, 0) + 1

    assert class_counts == stage0_baseline["class_counts"]
    assert format_counts == stage0_baseline["formats"]
    assert sum(1 for r in records if not r.readable) == stage0_baseline["unreadable_files"]
    assert all(r.status == "valid" for r in records)


def test_image_ids_are_deterministic_and_well_formed(raw_dir: Path, settings) -> None:
    paths = iter_candidate_files(raw_dir)
    first = [build_record(path, raw_dir, settings.class_defs())[0] for path in paths]
    second = [build_record(path, raw_dir, settings.class_defs())[0] for path in paths]

    for a, b in zip(first, second, strict=True):
        assert a.image_id == b.image_id, "image_id must be reproducible"
        assert IMAGE_ID_RE.match(a.image_id)
        expected = make_image_id(a.source_relative_path, a.sha256)
        assert a.image_id == expected


def test_content_sha256_is_correct(raw_dir: Path, settings) -> None:
    for path in iter_candidate_files(raw_dir):
        record, _ = build_record(path, raw_dir, settings.class_defs())
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert record.sha256 == actual
        assert record.file_size_bytes == path.stat().st_size


def test_source_paths_stay_inside_raw_dataset(raw_dir: Path, settings) -> None:
    for path in iter_candidate_files(raw_dir):
        record, _ = build_record(path, raw_dir, settings.class_defs())
        source = Path(record.source_path)
        assert source.is_relative_to(raw_dir)
        assert "/" in record.source_relative_path, "relative paths use forward slashes"
        assert "\\" not in record.source_relative_path


def test_unsupported_files_are_skipped(tmp_path: Path, raw_dir: Path) -> None:
    (tmp_path / "bell").mkdir()
    source = next(p for p in (raw_dir / "bell").iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    (tmp_path / "bell" / "photo.jpg").write_bytes(source.read_bytes())
    (tmp_path / "bell" / "notes.txt").write_text("not an image", encoding="utf-8")
    (tmp_path / "bell" / "Thumbs.db").write_bytes(b"\x00\x01")

    candidates = iter_candidate_files(tmp_path)
    assert [p.name for p in candidates] == ["photo.jpg"]
