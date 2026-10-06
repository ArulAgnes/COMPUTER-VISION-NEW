"""Path resolution and raw-data write protection.

Two categories of paths exist:

- RAW DATA: ``paths.raw_data_dir`` — read-only source images stored outside
  the repository. The application must never write, rename or delete here.
- GENERATED DATA: every other configured directory — always resolved inside
  the project repository.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import PathsConfig, get_settings, project_root


class RawDataViolationError(RuntimeError):
    """Raised when an operation attempts to write inside the raw dataset."""


def raw_data_dir() -> Path:
    """Absolute path of the read-only raw dataset."""
    return Path(get_settings().paths.raw_data_dir).expanduser().resolve()


def generated_dir(name: str) -> Path:
    """Resolve a configured generated directory relative to the project root.

    ``name`` is a key of :class:`~app.core.config.PathsConfig` other than
    ``raw_data_dir``.
    """
    if name == "raw_data_dir":
        raise ValueError("raw_data_dir is not a generated directory")
    relative = getattr(get_settings().paths, name)
    return (project_root() / relative).resolve()


def is_raw_path(path: Path | str) -> bool:
    """True when ``path`` resolves inside the read-only raw dataset."""
    try:
        return Path(path).expanduser().resolve().is_relative_to(raw_data_dir())
    except OSError:
        return False


def assert_not_raw(path: Path | str) -> None:
    """Raise :class:`RawDataViolationError` if ``path`` is inside raw data."""
    if is_raw_path(path):
        raise RawDataViolationError(
            f"refusing to write inside the read-only raw dataset: {path}"
        )


def generated_dir_names() -> list[str]:
    """Names of all configured generated directories."""
    return [
        field
        for field in PathsConfig.model_fields
        if field not in ("raw_data_dir", "baseline_file")
    ]


def ensure_generated_dirs() -> list[Path]:
    """Create all generated directories (idempotent). Never touches raw data."""
    created: list[Path] = []
    for name in generated_dir_names():
        target = generated_dir(name)
        assert_not_raw(target)
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            created.append(target)
    return created
