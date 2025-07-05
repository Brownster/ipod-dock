"""Logging configuration utilities for ipod_sync."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import config


DEFAULT_LOG_FILE = config.LOG_DIR / "ipod_sync.log"


def setup_logging(log_file: Path | str | None = None, level: int = logging.INFO) -> None:
    """Configure application logging.

    This sets up a :class:`~logging.handlers.RotatingFileHandler` that writes to
    ``logs/ipod_sync.log`` by default. Log files are rotated when they reach
    1 MB, keeping three backups.
    """

    path = Path(log_file) if log_file else DEFAULT_LOG_FILE
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(path, maxBytes=1_048_576, backupCount=3)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(logging.StreamHandler())

