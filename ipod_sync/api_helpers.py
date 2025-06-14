"""Helper functions used by the web API endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from . import config
from .libpod_wrapper import list_tracks, delete_track
from .utils import mount_ipod, eject_ipod

logger = logging.getLogger(__name__)


def save_to_queue(
    name: str,
    data: bytes,
    queue_dir: Path | None = None,
    category: str | None = None,
) -> Path:
    """Save uploaded file data to the sync queue directory.

    Parameters
    ----------
    name:
        Original filename of the uploaded content.
    data:
        File bytes to write.
    queue_dir:
        Destination directory for queued files. Defaults to
        :data:`~ipod_sync.config.SYNC_QUEUE_DIR`.
    category:
        Optional subdirectory for categorizing uploads (e.g. ``"music"`` or
        ``"audiobook"``). If provided the file will be written inside this
        subfolder.

    Returns
    -------
    Path
        The path to the written file.
    """
    queue = Path(queue_dir) if queue_dir else Path(config.SYNC_QUEUE_DIR)
    if category:
        queue = queue / category
    queue.mkdir(parents=True, exist_ok=True)
    dest = queue / name
    with dest.open("wb") as fh:
        fh.write(data)
    logger.info("Saved %s to queue", dest)
    return dest


def get_tracks(device: str = config.IPOD_DEVICE) -> list[dict]:
    """Mount the iPod and return a list of track metadata."""
    mount_ipod(device)
    try:
        return list_tracks()
    finally:
        eject_ipod()


def remove_track(db_id: str, device: str = config.IPOD_DEVICE) -> None:
    """Delete a track from the iPod by its database ID."""
    mount_ipod(device)
    try:
        delete_track(db_id)
    finally:
        eject_ipod()
