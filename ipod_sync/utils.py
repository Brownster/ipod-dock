"""Utility helpers for mounting and ejecting the iPod.

These helpers provide a small abstraction over the system ``mount`` and
``eject`` commands. They are intentionally thin wrappers so that higher level
modules do not need to worry about subprocess error handling or log output.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .config import IPOD_MOUNT

logger = logging.getLogger(__name__)


def _run(cmd: list[str]) -> None:
    """Run *cmd* via :mod:`subprocess` and raise ``RuntimeError`` on failure."""

    logger.debug("Running command: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True
        )
        if result.stdout:
            logger.debug(result.stdout.strip())
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Command '%s' failed with code %s: %s",
            " ".join(cmd),
            exc.returncode,
            exc.stderr.strip(),
        )
        raise RuntimeError(
            f"Command {' '.join(cmd)!r} failed: {exc.stderr.strip()}"
        ) from exc


def mount_ipod(device: str) -> None:
    """Mount the iPod ``device`` to :data:`~ipod_sync.config.IPOD_MOUNT`.

    Parameters
    ----------
    device:
        The block device path (e.g. ``/dev/sda1``) representing the iPod.
    """

    mount_point: Path = IPOD_MOUNT
    mount_point.mkdir(parents=True, exist_ok=True)
    logger.info("Mounting %s at %s", device, mount_point)
    _run(["mount", device, str(mount_point)])


def eject_ipod() -> None:
    """Unmount and eject the iPod currently mounted at
    :data:`~ipod_sync.config.IPOD_MOUNT`."""

    mount_point: Path = IPOD_MOUNT
    logger.info("Unmounting %s", mount_point)
    _run(["umount", str(mount_point)])
    logger.info("Ejecting %s", mount_point)
    _run(["eject", str(mount_point)])

