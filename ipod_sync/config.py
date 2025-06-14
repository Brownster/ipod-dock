"""Configuration for ipod_sync package."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNC_QUEUE_DIR = PROJECT_ROOT / "sync_queue"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOG_DIR = PROJECT_ROOT / "logs"

# Mount point of the iPod on the filesystem
IPOD_MOUNT = PROJECT_ROOT / "mnt" / "ipod"

