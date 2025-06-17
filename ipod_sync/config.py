"""Configuration for ipod_sync package."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNC_QUEUE_DIR = PROJECT_ROOT / "sync_queue"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOG_DIR = PROJECT_ROOT / "logs"

# Mount point of the iPod on the filesystem
IPOD_MOUNT = PROJECT_ROOT / "mnt" / "ipod"

# File used by the udev listener to record connection status
IPOD_STATUS_FILE = PROJECT_ROOT / "ipod_connected"

# Default block device representing the iPod. This can be overridden
# at runtime via command line arguments to the sync script.
IPOD_DEVICE = "/dev/disk/by-label/IPOD"

# Whether to keep a copy of files after they are successfully synced.
KEEP_LOCAL_COPY = False

# Shared secret used to authenticate API requests. Set the ``IPOD_API_KEY``
# environment variable to override. If ``None`` authentication is disabled.
API_KEY = os.getenv("IPOD_API_KEY")

# File extensions that can be synced without conversion.
SUPPORTED_FORMATS = {
    ".mp3",
    ".m4a",
    ".m4b",
    ".aac",
    ".aif",
    ".aiff",
    ".wav",
    ".alac",
}


# Serial port used for playback control
PLAYBACK_SERIAL_PORT = os.getenv("IPOD_SERIAL_PORT", "/dev/serial0")
PLAYBACK_BAUDRATE = int(os.getenv("IPOD_SERIAL_BAUD", "19200"))
