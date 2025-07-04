"""Utility helpers for mounting and ejecting the iPod.

These helpers provide a small abstraction over the system ``mount`` and
``eject`` commands. They are intentionally thin wrappers so that higher level
modules do not need to worry about subprocess error handling or log output.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import json
import shutil
import shlex
from typing import Any
from pathlib import Path

from .config import IPOD_MOUNT, IPOD_DEVICE, IPOD_STATUS_FILE
import time

LABEL_PATH = Path("/dev/disk/by-label/IPOD")
MOUNT_BIN = shutil.which("mount") or "/bin/mount"


def wait_for_label(timeout: float = 5.0) -> Path:
    """Return the resolved device node for ``/dev/disk/by-label/IPOD``."""

    deadline = time.time() + timeout
    while time.time() < deadline:
        if LABEL_PATH.exists():
            return LABEL_PATH.resolve()
        time.sleep(0.1)
    raise FileNotFoundError("iPod label path did not appear in time")

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


def _run(
    cmd: list[str],
    *,
    use_sudo: bool = False,
    check: bool = True,
    capture_output: bool = False,
    text: bool = True,
    log_level: int = logging.DEBUG,
    **popen_kw: Any,
) -> subprocess.CompletedProcess:
    """Run *cmd* via :mod:`subprocess`.

    ``use_sudo`` will prefix ``sudo --non-interactive --`` when not already
    running as root. The exact command is logged and a
    ``subprocess.CompletedProcess`` is returned so callers may inspect
    ``stdout`` or ``stderr`` if needed.
    """

    if use_sudo and os.geteuid() != 0:
        cmd = ["sudo", "--non-interactive", "--", *cmd]

    logger.log(log_level, "RUN: %s", " ".join(shlex.quote(c) for c in cmd))

    if capture_output:
        popen_kw.setdefault("stdout", subprocess.PIPE)
        popen_kw.setdefault("stderr", subprocess.PIPE)
    elif check:
        popen_kw.setdefault("stderr", subprocess.PIPE)

    proc = subprocess.run(cmd, check=False, text=text, **popen_kw)

    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr
        )

    return proc


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


def _ensure_sysinfo(device: str, mount_point: Path) -> None:
    """Create the ``SysInfoExtended`` file if missing."""

    sysinfo_path = mount_point / "iPod_Control" / "Device" / "SysInfoExtended"
    if sysinfo_path.exists():
        return

    tool = shutil.which("ipod-read-sysinfo-extended")
    if not tool:
        logger.debug("ipod-read-sysinfo-extended not found")
        return

    base_device = device
    try:
        result = subprocess.run(
            ["lsblk", "-no", "PKNAME", device],
            check=True,
            capture_output=True,
            text=True,
        )
        name = result.stdout.strip()
        if name:
            base_device = f"/dev/{name}"
    except Exception:
        base_device = re.sub(r"\d+$", "", str(device))

    try:
        _run([tool, base_device, str(mount_point)], use_sudo=True, capture_output=True, text=True)
        if sysinfo_path.exists():
            logger.info("Created SysInfoExtended at %s", sysinfo_path)
    except subprocess.CalledProcessError as exc:
        logger.error("Failed to create SysInfoExtended: %s", exc.stderr or exc)


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

    if str(device) == str(IPOD_DEVICE):
        try:
            device = str(wait_for_label())
        except FileNotFoundError:
            logger.debug("Label device not found; attempting auto-detection")
            device = detect_ipod_device()

    wait_for_device(device)

    mount_point: Path = IPOD_MOUNT
    if os.path.ismount(mount_point):
        logger.debug("%s already mounted", mount_point)
        try:
            Path(IPOD_STATUS_FILE).write_text("true")
        except Exception:
            logger.debug("Failed to update status file", exc_info=True)
        _ensure_sysinfo(device, mount_point)
        return
    mount_point.mkdir(parents=True, exist_ok=True)
    logger.info("Mounting %s at %s", device, mount_point)
    if not Path(device).exists():
        raise RuntimeError(f"{device} does not exist")
    try:
        _run(
            ["/usr/local/bin/mount-ipod", str(device)],
            use_sudo=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1 and "password" in (exc.stderr or "").lower():
            logger.error(
                "Mount failed: sudo requires a password. "
                "Add the ipod-dock sudoers rule or run the service as root."
            )
            return
        raise
    try:
        Path(IPOD_STATUS_FILE).write_text("true")
    except Exception:  # pragma: no cover - filesystem errors
        logger.debug("Failed to update status file", exc_info=True)

    _ensure_sysinfo(device, mount_point)


def eject_ipod() -> None:
    """Unmount and eject the iPod currently mounted at
    :data:`~ipod_sync.config.IPOD_MOUNT`."""

    mount_point: Path = IPOD_MOUNT
    if os.path.ismount(mount_point):
        logger.info("Unmounting %s", mount_point)
        _run(["umount", str(mount_point)], use_sudo=True, capture_output=True, text=True)
        logger.info("Ejecting %s", mount_point)
        _run(["eject", str(mount_point)], use_sudo=True, capture_output=True, text=True)
    else:
        logger.debug("%s not mounted", mount_point)
    try:
        Path(IPOD_STATUS_FILE).unlink(missing_ok=True)
    except Exception:  # pragma: no cover - filesystem errors
        logger.debug("Failed to remove status file", exc_info=True)
