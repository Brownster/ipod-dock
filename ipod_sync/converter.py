"""Audio conversion helpers."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


def needs_conversion(path: Path) -> bool:
    """Return ``True`` if *path* requires conversion."""
    return path.suffix.lower() not in config.SUPPORTED_FORMATS


def convert_audio(src: Path, dest: Path) -> None:
    """Convert *src* to MP3 at *dest* using ``ffmpeg``."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(dest),
    ]
    logger.info("Converting %s -> %s", src.name, dest.name)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg failed: %s", result.stderr.strip())
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")


def prepare_for_sync(path: Path) -> Path:
    """Convert ``path`` if needed and return the file to sync."""
    if needs_conversion(path):
        converted = path.with_suffix(".mp3")
        convert_audio(path, converted)
        return converted
    return path
