"""Utility helpers for mounting and ejecting the iPod.

These helpers provide a small abstraction over the system ``mount`` and
``eject`` commands. They are intentionally thin wrappers so that higher level
modules do not need to worry about subprocess error handling or log output.
"""

from __future__ import annotations

import logging
import subprocess
import json
from pathlib import Path

from .config import IPOD_MOUNT, IPOD_DEVICE, IPOD_STATUS_FILE
import time

logger = logging.getLogger(__name__)


def wait_for_device(path: str | Path, timeout: float = 5.0) -> bool:
    """Return ``True`` when *path* exists within *timeout* seconds."""
    dev = Path(path)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if dev.exists():
            return True
        time.sleep(0.1)
    return dev.exists()


def _run(cmd: list[str]) -> None:
    """Run *cmd* via :mod:`subprocess` and raise ``RuntimeError`` on failure."""

    logger.debug("Running command: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
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
    """Return the largest FAT formatted block device detected by ``lsblk``.

    The helper parses ``lsblk`` JSON output and selects the biggest partition
    reporting ``vfat`` (or ``fat``) as its filesystem type.  If detection fails
    or no FAT partition is found, :data:`~ipod_sync.config.IPOD_DEVICE` is
    returned as a fallback.
    """

    try:
        result = subprocess.run(
            ["lsblk", "--json", "-b", "-o", "NAME,FSTYPE,SIZE"],
            check=True,
            capture_output=True,
            text=True,
        )
        info = json.loads(result.stdout)
        candidates: list[tuple[int, str]] = []
        for dev in info.get("blockdevices", []):
            for part in dev.get("children", []) or []:
                fstype = (part.get("fstype") or "").lower()
                if fstype in {"vfat", "fat"}:
                    size = int(part.get("size", 0))
                    candidates.append((size, part["name"]))
        if candidates:
            _, name = max(candidates, key=lambda p: p[0])
            return f"/dev/{name}"
    except Exception:  # pragma: no cover - system command may fail
        logger.debug("Failed to detect iPod device", exc_info=True)

    return IPOD_DEVICE


def mount_ipod(device: str | None = None) -> None:
    """Mount the iPod ``device`` to :data:`~ipod_sync.config.IPOD_MOUNT`.

    Parameters
    ----------
    device:
        The block device path (e.g. ``/dev/disk/by-label/IPOD``) representing
        the iPod. If
        ``None`` the device is determined automatically via
        :func:`detect_ipod_device`.
    """

    if device is None:
        device = detect_ipod_device()

    wait_for_device(IPOD_DEVICE)

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
    try:
        Path(IPOD_STATUS_FILE).write_text("true")
    except Exception:  # pragma: no cover - filesystem errors
        logger.debug("Failed to update status file", exc_info=True)


def eject_ipod() -> None:
    """Unmount and eject the iPod currently mounted at
    :data:`~ipod_sync.config.IPOD_MOUNT`."""

    mount_point: Path = IPOD_MOUNT
    logger.info("Unmounting %s", mount_point)
    _run(["umount", str(mount_point)])
    logger.info("Ejecting %s", mount_point)
    _run(["eject", str(mount_point)])
    try:
        Path(IPOD_STATUS_FILE).unlink(missing_ok=True)
    except Exception:  # pragma: no cover - filesystem errors
        logger.debug("Failed to remove status file", exc_info=True)
