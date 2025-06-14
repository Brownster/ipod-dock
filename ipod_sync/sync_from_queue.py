"""Simple script to sync files from :data:`~ipod_sync.config.SYNC_QUEUE_DIR`.

The script mounts the iPod, imports any files found in the queue using
:func:`~ipod_sync.libpod_wrapper.add_track`, and then ejects the device.
Files are deleted from the queue after successful import unless
:data:`~ipod_sync.config.KEEP_LOCAL_COPY` is set to ``True``.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import config
from .libpod_wrapper import add_track
from .utils import mount_ipod, eject_ipod

logger = logging.getLogger(__name__)


def sync_queue(device: str = config.IPOD_DEVICE) -> None:
    """Process all files waiting in the sync queue.

    Parameters
    ----------
    device:
        Block device path representing the iPod.
    """

    queue = Path(config.SYNC_QUEUE_DIR)
    queue.mkdir(parents=True, exist_ok=True)

    files = [f for f in sorted(queue.iterdir()) if f.is_file()]
    if not files:
        logger.info("No files to sync in %s", queue)
        return

    mount_ipod(device)
    try:
        for file in files:
            try:
                track_id = add_track(file)
                size = file.stat().st_size
                logger.info(
                    "Synced %s (%d bytes) track_id=%s", file.name, size, track_id
                )
                if not config.KEEP_LOCAL_COPY:
                    file.unlink()
                    logger.debug("Deleted %s", file)
            except Exception as exc:  # pragma: no cover - unexpected failures
                logger.error("Failed to sync %s: %s", file, exc)
    finally:
        eject_ipod()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sync queued files to an iPod")
    parser.add_argument(
        "--device",
        default=config.IPOD_DEVICE,
        help="Path to iPod block device (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    sync_queue(args.device)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
