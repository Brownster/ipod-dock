"""Utility helpers for mounting and ejecting the iPod."""

import subprocess
from pathlib import Path

from .config import IPOD_MOUNT


def mount_ipod(device: str) -> None:
    """Mount the iPod device to the configured mount point."""
    raise NotImplementedError("mount_ipod() not yet implemented")


def eject_ipod() -> None:
    """Eject the iPod safely."""
    raise NotImplementedError("eject_ipod() not yet implemented")

