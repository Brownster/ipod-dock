"""Simple script to sync files from :data:`~ipod_sync.config.SYNC_QUEUE_DIR`.

Files are deleted from the queue after successful import unless
:data:`~ipod_sync.config.KEEP_LOCAL_COPY` is set to ``True``.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import config
from .logging_setup import setup_logging
from .libpod_wrapper import add_track, LibpodError
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
    queue = Path(config.SYNC_QUEUE_DIR)
    queue.mkdir(parents=True, exist_ok=True)

    files = [f for f in sorted(queue.rglob('*')) if f.is_file()]
    if not files:
        logger.info("No files to sync in %s", queue)
        return

    mount_ipod(mount_point)

    logger.info("Starting sync to %s", mount_point)
    for file in files:
        try:
            to_sync = converter.prepare_for_sync(file)
            track_id = add_track(to_sync)
            size = to_sync.stat().st_size
            logger.info(
                "Synced %s (%d bytes) track_id=%s",
                to_sync.name,
                size,
                track_id,
            )
            if not config.KEEP_LOCAL_COPY:
                file.unlink(missing_ok=True)
                if to_sync != file:
                    to_sync.unlink(missing_ok=True)
                logger.debug("Deleted %s", file)
        except LibpodError as exc:
            logger.error("Failed to sync %s: %s", file, exc)
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error("Failed to sync %s: %s", file, exc)
    logger.info("Sync finished")
    eject_ipod()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sync queued files to an iPod")
    parser.add_argument(
        "--device",
        dest="mount_point",
        default=str(config.IPOD_MOUNT),
        help="Path to iPod mount point",
    )
    args = parser.parse_args(argv)

    sync_queue(args.mount_point)


if __name__ == "__main__":
    setup_logging()
    main()
