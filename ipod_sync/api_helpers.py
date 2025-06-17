"""Helper functions used by the web API endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from . import config
from .libpod_wrapper import (
    list_tracks,
    delete_track,
    list_playlists,
    create_playlist,
)
from .utils import mount_ipod, eject_ipod

logger = logging.getLogger(__name__)


def is_ipod_connected(device: str = config.IPOD_DEVICE) -> bool:
    """Return ``True`` if the iPod device exists or is mounted."""
    dev = Path(device)
    if dev.exists():
        return True
    try:
        with open("/proc/mounts", "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if parts and parts[0] == str(device):
                    return True
    except Exception:  # pragma: no cover - platform specific failures
        return False
    return False


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


def get_playlists(device: str = config.IPOD_DEVICE) -> list[dict]:
    """Mount the iPod and return a list of playlists."""
    mount_ipod(device)
    try:
        return list_playlists()
    finally:
        eject_ipod()


def remove_track(db_id: str, device: str = config.IPOD_DEVICE) -> None:
    """Delete a track from the iPod by its database ID."""
    mount_ipod(device)
    try:
        delete_track(db_id)
    finally:
        eject_ipod()


def create_new_playlist(name: str, track_ids: list[str], device: str = config.IPOD_DEVICE) -> None:
    """Create a playlist with ``track_ids`` on the iPod."""
    mount_ipod(device)
    try:
        create_playlist(name, track_ids)
    finally:
        eject_ipod()


def list_queue(queue_dir: Path | None = None) -> list[dict]:
    """Return information about files waiting in the sync queue."""
    queue = Path(queue_dir) if queue_dir else Path(config.SYNC_QUEUE_DIR)
    if not queue.exists():
        return []
    files = []
    for path in queue.rglob('*'):
        if path.is_file():
            files.append({
                'name': path.name,
                'size': path.stat().st_size,
            })
    return files


def clear_queue(queue_dir: Path | None = None) -> None:
    """Remove all files from the sync queue."""
    queue = Path(queue_dir) if queue_dir else Path(config.SYNC_QUEUE_DIR)
    if not queue.exists():
        return
    for path in queue.rglob('*'):
        if path.is_file():
            path.unlink()


def get_stats(device: str = config.IPOD_DEVICE, queue_dir: Path | None = None) -> dict:
    """Return basic statistics for the web UI."""
    tracks = get_tracks(device)
    queue_files = list_queue(queue_dir)

    try:
        import shutil
        usage = shutil.disk_usage(config.PROJECT_ROOT)
        used_percent = int(usage.used / usage.total * 100)
    except Exception:  # pragma: no cover - platform specific failures
        used_percent = 0

    return {
        'music': len(tracks),
        'audiobooks': 0,
        'podcasts': 0,
        'queue': len(queue_files),
        'storage_used': used_percent,
    }
