"""Simple script to sync files from :data:`~ipod_sync.config.SYNC_QUEUE_DIR`.

Files are deleted from the queue after successful import unless
:data:`~ipod_sync.config.KEEP_LOCAL_COPY` is set to ``True``.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import config_manager
from .logging_setup import setup_logging
from .repositories.factory import get_ipod_repo
from .repositories import Track
from . import converter
from .utils import mount_ipod, eject_ipod

logger = logging.getLogger(__name__)


def sync_queue(mount_point: str) -> None:
    """Process all files waiting in the sync queue.

    Parameters
    ----------
    mount_point:
        The path where the iPod is mounted.
    """
    queue = Path(config_manager.config.sync_queue_dir)
    queue.mkdir(parents=True, exist_ok=True)

    files = [f for f in sorted(queue.rglob('*')) if f.is_file()]
    if not files:
        logger.info("No files to sync in %s", queue)
        return

    mount_ipod(mount_point)

    logger.info("Starting sync to %s", mount_point)
    for file in files:
        try:
            repo = get_ipod_repo(mount_point)
            to_sync = converter.prepare_for_sync(file)
            track = Track(title=to_sync.stem, file_path=str(to_sync))
            track_id = repo.add_track(track)
            size = to_sync.stat().st_size
            logger.info(
                "Synced %s (%d bytes) track_id=%s",
                to_sync.name,
                size,
                track_id,
            )
            if not config_manager.config.keep_local_copy:
                file.unlink(missing_ok=True)
                if to_sync != file:
                    to_sync.unlink(missing_ok=True)
                logger.debug("Deleted %s", file)
        except Exception as exc:
            logger.error("Failed to sync %s: %s", file, exc)
    logger.info("Sync finished")
    eject_ipod()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sync queued files to an iPod")
    parser.add_argument(
        "--device",
        dest="mount_point",
        default=str(config_manager.config.ipod.mount_point),
        help="Path to iPod mount point",
    )
    args = parser.parse_args(argv)

    sync_queue(args.mount_point)


if __name__ == "__main__":
    setup_logging()
    main()
