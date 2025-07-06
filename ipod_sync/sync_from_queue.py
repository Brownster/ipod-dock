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
from . import metadata

logger = logging.getLogger(__name__)


def _extract_metadata(file_path: Path) -> dict:
    """Extract metadata from audio file."""
    try:
        # Try to use the metadata module from the project
        return metadata.extract_metadata(str(file_path))
    except Exception as e:
        logger.warning("Failed to extract metadata from %s: %s", file_path, e)
        return {}


def _determine_file_category(file_path: Path) -> str:
    """Determine category based on file path and name."""
    path_str = str(file_path).lower()
    name_str = file_path.name.lower()
    
    # Check for audiobook indicators
    if any(indicator in path_str for indicator in ['audiobook', 'audible', '.m4b']):
        return 'audiobook'
    
    # Check for podcast indicators
    if any(indicator in path_str for indicator in ['podcast', 'podcasts']):
        return 'podcast'
    
    # Check file extension for audiobooks
    if file_path.suffix.lower() in ['.m4b', '.aa', '.aax']:
        return 'audiobook'
    
    return 'music'


def sync_queue(device_or_mount_point: str) -> None:
    """Process all files waiting in the sync queue.

    Parameters
    ----------
    device_or_mount_point:
        Either a device path (like /dev/sdc2) to mount, or an already mounted path.
    """
    queue = Path(config_manager.config.sync_queue_dir)
    queue.mkdir(parents=True, exist_ok=True)

    files = [f for f in sorted(queue.rglob('*')) if f.is_file()]
    if not files:
        logger.info("No files to sync in %s", queue)
        return

    # Determine if we need to mount or if it's already mounted
    if device_or_mount_point.startswith('/dev/'):
        # It's a device path, we need to mount it
        mount_ipod(device_or_mount_point)
        mount_point = str(config_manager.config.ipod.mount_point)
    else:
        # It's already a mount point path
        mount_point = device_or_mount_point
        logger.debug("Using existing mount point: %s", mount_point)

    logger.info("Starting sync to %s", mount_point)
    repo = None
    success_count = 0
    error_count = 0
    
    try:
        repo = get_ipod_repo(mount_point)
        
        for file in files:
            try:
                to_sync = converter.prepare_for_sync(file)
                
                # Extract metadata from file using mutagen or similar
                metadata = _extract_metadata(to_sync)
                
                track = Track(
                    id=str(to_sync),
                    title=metadata.get('title') or to_sync.stem,
                    artist=metadata.get('artist'),
                    album=metadata.get('album'),
                    genre=metadata.get('genre'),
                    track_number=metadata.get('track_number'),
                    file_path=str(to_sync),
                    category=_determine_file_category(to_sync)
                )
                
                track_id = repo.add_track(track)
                size = to_sync.stat().st_size
                logger.info(
                    "Synced %s (%d bytes) track_id=%s [%s - %s]",
                    to_sync.name,
                    size,
                    track_id,
                    track.artist or 'Unknown Artist',
                    track.title
                )
                
                if not config_manager.config.keep_local_copy:
                    file.unlink(missing_ok=True)
                    if to_sync != file:
                        to_sync.unlink(missing_ok=True)
                    logger.debug("Deleted %s", file)
                
                success_count += 1
                
            except Exception as exc:
                logger.error("Failed to sync %s: %s", file, exc)
                error_count += 1
                
        # Save all changes to iPod database
        if repo and success_count > 0:
            logger.info("Saving changes to iPod database...")
            try:
                if repo.save_changes():
                    logger.info("Successfully saved %d tracks to iPod", success_count)
                else:
                    logger.error("Failed to save changes to iPod database")
                    error_count += len(files) - success_count  # Mark remaining as errors
            except Exception as save_error:
                logger.error("Exception during save_changes(): %s", save_error)
                error_count += len(files) - success_count
                
    except Exception as exc:
        logger.error("Failed to initialize iPod repository: %s", exc)
        
    logger.info("Sync finished: %d successful, %d errors", success_count, error_count)
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
