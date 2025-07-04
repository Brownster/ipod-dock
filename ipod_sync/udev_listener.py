"""Listen for iPod USB events and trigger syncing."""

from __future__ import annotations

import argparse
import logging
import subprocess
import time
from typing import Iterable, Tuple

import pyudev

from . import config
from .logging_setup import setup_logging
from .sync_from_queue import sync_queue
from . import utils
from pathlib import Path

# Path used to indicate connection status to other components
STATUS_FILE = Path(config.IPOD_STATUS_FILE)
MOUNT_POINT = "/opt/ipod-dock/mnt/ipod"
MOUNT_USER = "ipod"

logger = logging.getLogger(__name__)


def get_mount_uid_gid() -> Tuple[int, int]:
    """Get UID and GID for the mount user."""
    try:
        uid = int(subprocess.check_output(["id", "-u", MOUNT_USER]).strip())
        gid = int(subprocess.check_output(["id", "-g", MOUNT_USER]).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        uid, gid = 1000, 1000  # Default to 1000 if user not found
    return uid, gid


def find_ipod_partition(device: pyudev.Device) -> str | None:
    """Find the largest VFAT partition on the given device."""
    time.sleep(1)  # Give partitions time to be detected
    partitions = device.parent.children
    vfat_partitions = [
        p for p in partitions if p.get("ID_FS_TYPE") in ("vfat", "fat32")
    ]

    if not vfat_partitions:
        return None

    # Return the largest partition
    return max(vfat_partitions, key=lambda p: p.get("size", 0)).device_node


def mount_partition(partition: str, uid: int, gid: int) -> bool:
    """Mount the partition to the designated mount point."""
    if subprocess.run(["mountpoint", "-q", MOUNT_POINT]).returncode == 0:
        logger.info("Mount point %s is already in use.", MOUNT_POINT)
        return True  # Assume it's already mounted correctly

    Path(MOUNT_POINT).mkdir(parents=True, exist_ok=True)
    mount_cmd = [
        "mount",
        "-t",
        "vfat",
        "-o",
        f"uid={uid},gid={gid},umask=000,nosuid,nodev,noatime",
        partition,
        MOUNT_POINT,
    ]
    result = subprocess.run(mount_cmd)
    if result.returncode == 0:
        logger.info("Mounted %s to %s", partition, MOUNT_POINT)
        return True
    else:
        logger.error("Failed to mount %s: %s", partition, result.stderr)
        return False


def unmount_partition() -> None:
    """Unmount the iPod partition."""
    if subprocess.run(["mountpoint", "-q", MOUNT_POINT]).returncode == 0:
        if subprocess.run(["umount", MOUNT_POINT]).returncode == 0:
            logger.info("Unmounted %s", MOUNT_POINT)
        else:
            logger.error("Failed to unmount %s", MOUNT_POINT)


def _set_connected(connected: bool) -> None:
    """Create or remove the status file to reflect connection state."""
    try:
        if connected:
            STATUS_FILE.write_text("1")
        else:
            if STATUS_FILE.exists():
                STATUS_FILE.unlink()
    except Exception:  # pragma: no cover - filesystem errors
        logger.debug("Failed to update status file", exc_info=True)


def listen(
    device: str | None = None,
    vendor: str = "05ac",
    product: str = "1209",
    monitor: Iterable[Tuple[str, pyudev.Device]] | None = None,
) -> None:
    """Listen for matching USB device events and sync on attach."""
    if monitor is None:
        ctx = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(ctx)
        monitor.filter_by("usb")
        monitor = iter(monitor)

    logger.info("Listening for iPod USB events")
    _set_connected(False)
    uid, gid = get_mount_uid_gid()

    for action, dev in monitor:
        if dev.get("ID_VENDOR_ID") == vendor and dev.get("ID_MODEL_ID") == product:
            serial = dev.get("ID_SERIAL_SHORT", "unknown")
            logger.debug("Event %s for %s", action, serial)

            if action == "add" and dev.device_type in {"usb_device", "partition"}:
                target = device or dev.device_node
                logger.info("iPod %s attached", serial)
                _set_connected(True)
                try:
                    sync_queue(target)
                except Exception as exc:  # pragma: no cover - runtime errors
                    logger.error("Failed to sync: %s", exc)

            elif action == "remove" and dev.device_type == "usb_device":
                logger.info("iPod %s removed", serial)
                unmount_partition()
                _set_connected(False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Listen for iPod USB events")
    parser.add_argument("--device", help="iPod mount point")
    parser.add_argument("--vendor", default="05ac", help="USB vendor ID")
    parser.add_argument("--product", default="1209", help="USB product ID")
    args = parser.parse_args(argv)

    setup_logging()
    listen(args.device, args.vendor, args.product)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
