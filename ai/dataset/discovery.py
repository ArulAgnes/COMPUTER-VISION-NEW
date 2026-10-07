"""Dataset discovery: recursively scan the raw dataset and build manifest records.

The raw directory is strictly read-only: this module only opens files for
reading and never writes, renames or moves anything inside it.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image

from ai.dataset.models import (
    NO_CLASS,
    UNKNOWN_CLASS,
    UNREADABLE,
    VALID,
    ManifestRecord,
)
from ai.dataset.settings import ClassDef

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

_HASH_CHUNK = 1 << 20


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compute_sha256(path: Path) -> str:
    """Streaming SHA-256 of the file contents (real hash, no approximation)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_image_id(relative_path: str, content_sha256: str) -> str:
    """Deterministic id: same source file => same id, no random UUIDs.

    Combines the stable relative path with the content hash so exact
    duplicates in different folders remain separately addressable while the
    content identity stays available in ``sha256``.
    """
    payload = f"{relative_path}\0{content_sha256}".encode("utf-8")
    return "img_" + hashlib.sha256(payload).hexdigest()


def iter_candidate_files(raw_dir: Path) -> list[Path]:
    """Sorted list of supported image files under ``raw_dir`` (deterministic order)."""
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"raw dataset directory not found: {raw_dir}")
    candidates: list[Path] = []
    for root, dirs, files in os.walk(raw_dir):
        dirs.sort()
        for name in sorted(files):
            if Path(name).suffix.lower() in SUPPORTED_EXTENSIONS:
                candidates.append(Path(root) / name)
    candidates.sort(key=lambda p: p.relative_to(raw_dir).as_posix())
    return candidates


@dataclass
class DecodeResult:
    """Outcome of actually decoding one image."""

    readable: bool
    width: int | None
    height: int | None
    channels: int | None
    color_mode: str | None
    gray: np.ndarray | None
    decode_error: str | None


def decode_image(path: Path) -> DecodeResult:
    """Decode with Pillow (metadata) and OpenCV (pixels).

    Failures are captured per image — a corrupted file never aborts the scan.
    """
    width: int | None = None
    height: int | None = None
    channels: int | None = None
    color_mode: str | None = None
    pil_error: str | None = None

    try:
        with Image.open(path) as img:
            width, height = img.size
            color_mode = img.mode
            channels = len(img.getbands())
    except Exception as exc:
        pil_error = f"Pillow: {type(exc).__name__}: {exc}"

    pixels = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if pixels is None:
        cv_error = "OpenCV: imread failed (corrupted or unsupported image data)"
        error = " | ".join(e for e in (pil_error, cv_error) if e)
        return DecodeResult(False, width, height, channels, color_mode, None, error)

    gray = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    if width is None or height is None:
        height, width = pixels.shape[:2]
    if channels is None:
        channels = int(pixels.shape[2]) if pixels.ndim == 3 else 1
    return DecodeResult(True, int(width), int(height), channels, color_mode, gray, None)


def resolve_class(
    relative_path: str, classes: Sequence[ClassDef]
) -> tuple[str | None, int | None, str]:
    """Map the first folder of ``relative_path`` to a configured class.

    Returns ``(class_name, class_id, status)``; unknown folders are recorded
    instead of raising, so configuration mistakes stay visible.
    """
    parts = relative_path.split("/")
    if len(parts) < 2:
        return None, None, NO_CLASS
    folder = parts[0]
    for cls in classes:
        if cls.name == folder:
            return cls.name, cls.id, VALID
    return folder, None, UNKNOWN_CLASS


def build_record(
    path: Path, raw_dir: Path, classes: Sequence[ClassDef]
) -> tuple[ManifestRecord, np.ndarray | None]:
    """Read one image and build its manifest record.

    Returns ``(record, grayscale_pixels)``; pixels are ``None`` when unreadable.
    """
    relative = path.relative_to(raw_dir).as_posix()
    file_size = path.stat().st_size
    sha256 = compute_sha256(path)
    image_id = make_image_id(relative, sha256)
    class_name, class_id, class_status = resolve_class(relative, classes)

    decoded = decode_image(path)
    status = UNREADABLE if not decoded.readable else class_status

    record = ManifestRecord(
        image_id=image_id,
        source_path=str(path.resolve()),
        source_relative_path=relative,
        class_name=class_name,
        class_id=class_id,
        filename=path.name,
        extension=path.suffix.lower().lstrip("."),
        width=decoded.width,
        height=decoded.height,
        channels=decoded.channels,
        color_mode=decoded.color_mode,
        file_size_bytes=file_size,
        sha256=sha256,
        readable=decoded.readable,
        decode_error=decoded.decode_error,
        status=status,
        discovery_timestamp=utc_now_iso(),
    )
    return record, decoded.gray
