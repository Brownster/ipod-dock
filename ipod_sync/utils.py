"""Utility helpers for mounting and ejecting the iPod.

These helpers provide a small abstraction over the system ``mount`` and
``eject`` commands. They are intentionally thin wrappers so that higher level
modules do not need to worry about subprocess error handling or log output.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .config import IPOD_MOUNT, IPOD_DEVICE

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


def detect_ipod_device() -> str:
    """Detect the iPod's block device partition.

    Enumerates block devices via ``lsblk`` and returns the first partition
    reporting ``vfat`` or ``FAT`` as its filesystem type.  If detection fails
    or no FAT partition is found, :data:`~ipod_sync.config.IPOD_DEVICE` is
    returned as a fallback.
    """

    try:
        result = subprocess.run(
            ["lsblk", "-rno", "NAME,FSTYPE"],
            check=True,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].lower() in {"vfat", "fat"}:
                return f"/dev/{parts[0]}"
    except Exception:  # pragma: no cover - system command may fail
        logger.debug("Failed to detect iPod device", exc_info=True)

    return IPOD_DEVICE


def mount_ipod(device: str | None = None) -> None:
    """Mount the iPod ``device`` to :data:`~ipod_sync.config.IPOD_MOUNT`.

    Parameters
    ----------
    device:
        The block device path (e.g. ``/dev/sda1``) representing the iPod. If
        ``None`` the device is determined automatically via
        :func:`detect_ipod_device`.
    """

    if device is None:
        device = detect_ipod_device()

    mount_point: Path = IPOD_MOUNT
    mount_point.mkdir(parents=True, exist_ok=True)
    logger.info("Mounting %s at %s", device, mount_point)
    # When ``user`` mount permissions are configured in ``/etc/fstab`` a
    # non-root user may only specify one of the mount point **or** device
    # name. Passing both causes ``mount`` to abort with "must be superuser"
    # even if the user is permitted to mount the device. Using only the
    # mount point relies on the ``fstab`` entry to look up the device and
    # works correctly for unprivileged users.
    _run(["mount", str(mount_point)])


def eject_ipod() -> None:
    """Unmount and eject the iPod currently mounted at
    :data:`~ipod_sync.config.IPOD_MOUNT`."""

    mount_point: Path = IPOD_MOUNT
    logger.info("Unmounting %s", mount_point)
    _run(["umount", str(mount_point)])
    logger.info("Ejecting %s", mount_point)
    _run(["eject", str(mount_point)])

