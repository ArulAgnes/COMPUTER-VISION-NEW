"""Structured application logging.

Logs go to stdout and to ``logs/api.log`` (git-ignored). Secrets must never
be logged.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOGGER_NAME = "cvplatform"


def setup_logging(logs_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure the application logger (idempotent)."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if logs_dir is not None:
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(logs_dir / "api.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            logger.warning("could not open log file in %s; stdout logging only", logs_dir)

    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced application logger."""
    base = logging.getLogger(LOGGER_NAME)
    return base.getChild(name) if name else base
