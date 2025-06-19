from __future__ import annotations

"""Helpers for downloading audio from YouTube URLs using ``yt-dlp``."""

import logging
from pathlib import Path

from yt_dlp import YoutubeDL

from . import config

logger = logging.getLogger(__name__)


def download_audio(
    url: str, category: str = "music", queue_dir: Path | None = None
) -> Path:
    """Download *url* and return the queued file path.

    Parameters
    ----------
    url:
        YouTube URL to download.
    category:
        One of ``"music"``, ``"audiobook"`` or ``"podcast"`` determining the
        subdirectory under the queue where the file will be placed.
    queue_dir:
        Base queue directory. Defaults to ``config.SYNC_QUEUE_DIR``.
    """
    queue = Path(queue_dir) if queue_dir else Path(config.SYNC_QUEUE_DIR)
    if category:
        queue = queue / category
    queue.mkdir(parents=True, exist_ok=True)

    outtmpl = str(queue / "%(title)s.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    logger.info("Downloading %s to %s", url, queue)
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
    logger.info("Downloaded %s", filename.name)
    return filename
