"""Filesystem watcher that triggers syncing when new files arrive."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import config_manager
from .logging_setup import setup_logging
from .sync_from_queue import sync_queue

logger = logging.getLogger(__name__)


_TEMP_SUFFIXES = (".tmp", ".swp", "~", ".part")


def _should_ignore(path: str) -> bool:
    """Return ``True`` if *path* should not trigger a sync."""
    name = Path(path).name
    return name.startswith(".") or name.endswith(_TEMP_SUFFIXES)


class QueueEventHandler(FileSystemEventHandler):
    """Handle filesystem events from the sync queue."""

    def __init__(self, device: str | None = None, dry_run: bool = False) -> None:
        super().__init__()
        self.device = device
        self.dry_run = dry_run

    def _process(self, path: str) -> None:
        if _should_ignore(path):
            logger.debug("Ignoring temporary file %s", path)
            return
        logger.info("Detected new file %s", Path(path).name)
        try:
            if self.dry_run:
                logger.info("Dry-run: would sync queue")
            else:
                sync_queue(self.device)
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error("Failed to process queue: %s", exc)

    def on_created(self, event) -> None:  # noqa: D401
        if not event.is_directory:
            self._process(event.src_path)

    def on_moved(self, event) -> None:  # noqa: D401
        if not event.is_directory:
            self._process(event.dest_path)

    def on_closed(self, event) -> None:  # noqa: D401
        if not event.is_directory:
            self._process(event.src_path)


def watch(queue_dir: Path, device: str | None = None, dry_run: bool = False) -> None:
    """Start watching *queue_dir* for new files."""
    queue_dir = Path(queue_dir)
    queue_dir.mkdir(parents=True, exist_ok=True)

    handler = QueueEventHandler(device, dry_run=dry_run)
    observer = Observer()
    observer.schedule(handler, str(queue_dir), recursive=False)
    observer.start()
    logger.info("Watching %s", queue_dir)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher")
    finally:
        observer.stop()
        observer.join()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Watch a directory and sync files to an iPod"
    )
    parser.add_argument(
        "--queue-dir",
        default=config_manager.config.sync_queue_dir,
        type=Path,
        help="Directory containing queued files",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Path to iPod block device",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log events without syncing",
    )
    args = parser.parse_args(argv)

    setup_logging()
    watch(args.queue_dir, args.device, dry_run=args.dry_run)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
