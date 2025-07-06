"""Listen for iPod USB events and trigger syncing."""

from __future__ import annotations

import argparse
import logging
import subprocess
import time
from typing import Iterable, Tuple

import pyudev

from .config import config_manager
from .logging_setup import setup_logging
from .sync_from_queue import sync_queue
from . import utils
from pathlib import Path

# Path used to indicate connection status to other components
STATUS_FILE = Path(config_manager.config.project_root) / "ipod_connected"
MOUNT_POINT = str(config_manager.config.ipod.mount_point)
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
    
    try:
        partitions = device.parent.children
        vfat_partitions = [
            p for p in partitions if p.get("ID_FS_TYPE") in ("vfat", "fat32")
        ]

        if not vfat_partitions:
            logger.debug("No VFAT partitions found on device %s", device.device_node)
            return None

        # Return the largest partition (usually the second partition on iPods)
        largest_partition = max(vfat_partitions, key=lambda p: int(p.get("size", 0)))
        logger.debug("Found VFAT partition: %s (size: %s)", largest_partition.device_node, largest_partition.get("size"))
        return largest_partition.device_node
    except Exception as e:
        logger.error("Error finding iPod partition: %s", e)
        return None


def _verify_mount(mount_point: str) -> bool:
    """Verify that the mount point is accessible and contains iPod structure."""
    try:
        mount_path = Path(mount_point)
        if not mount_path.exists():
            return False
        
        # Check for iPod Control directory
        ipod_control = mount_path / "iPod_Control"
        if not ipod_control.exists():
            logger.warning("iPod_Control directory not found at %s", mount_point)
            return False
        
        # Check for iTunes directory
        itunes_dir = ipod_control / "iTunes"
        if not itunes_dir.exists():
            logger.warning("iTunes directory not found at %s", mount_point)
            return False
        
        # Check for Music directory
        music_dir = ipod_control / "Music"
        if not music_dir.exists():
            logger.warning("Music directory not found at %s", mount_point)
            return False
        
        logger.debug("Mount verification successful for %s", mount_point)
        return True
    except Exception as e:
        logger.error("Error verifying mount %s: %s", mount_point, e)
        return False


def mount_partition(partition: str, uid: int, gid: int) -> bool:
    """Mount the partition to the designated mount point with proper permissions."""
    if subprocess.run(["mountpoint", "-q", MOUNT_POINT]).returncode == 0:
        logger.info("Mount point %s is already in use.", MOUNT_POINT)
        return True  # Assume it's already mounted correctly

    Path(MOUNT_POINT).mkdir(parents=True, exist_ok=True)
    
    # Updated mount options based on testing:
    # - uid/gid for user access
    # - umask=0022 for reasonable permissions (755 for dirs, 644 for files)
    # - nosuid,nodev,noatime for security and performance
    # - rw for read-write access
    mount_cmd = [
        "mount",
        "-t",
        "vfat",
        "-o",
        f"uid={uid},gid={gid},umask=0022,rw,nosuid,nodev,noatime",
        partition,
        MOUNT_POINT,
    ]
    
    try:
        result = subprocess.run(mount_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info("Mounted %s to %s with uid=%d,gid=%d", partition, MOUNT_POINT, uid, gid)
            
            # Verify the mount worked and we can access it
            if _verify_mount(MOUNT_POINT):
                return True
            else:
                logger.error("Mount verification failed for %s", MOUNT_POINT)
                unmount_partition()
                return False
        else:
            logger.error("Failed to mount %s: %s", partition, result.stderr)
            return False
    except subprocess.TimeoutExpired:
        logger.error("Mount command timed out for %s", partition)
        return False
    except Exception as e:
        logger.error("Unexpected error mounting %s: %s", partition, e)
        return False


def unmount_partition() -> None:
    """Unmount the iPod partition with proper error handling."""
    if subprocess.run(["mountpoint", "-q", MOUNT_POINT]).returncode == 0:
        try:
            # Try graceful unmount first
            result = subprocess.run(["umount", MOUNT_POINT], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("Unmounted %s", MOUNT_POINT)
            else:
                logger.warning("Graceful unmount failed: %s", result.stderr)
                # Try force unmount
                result = subprocess.run(["umount", "-f", MOUNT_POINT], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info("Force unmounted %s", MOUNT_POINT)
                else:
                    logger.error("Failed to unmount %s: %s", MOUNT_POINT, result.stderr)
        except subprocess.TimeoutExpired:
            logger.error("Unmount command timed out for %s", MOUNT_POINT)
        except Exception as e:
            logger.error("Unexpected error unmounting %s: %s", MOUNT_POINT, e)
    else:
        logger.debug("Mount point %s is not mounted", MOUNT_POINT)


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
                logger.info("iPod %s attached", serial)
                _set_connected(True)
                try:
                    # Find the correct VFAT partition
                    partition = find_ipod_partition(dev)
                    if not partition:
                        logger.error("Could not find VFAT partition on iPod")
                        continue
                    
                    logger.info("Found iPod partition: %s", partition)
                    
                    # Mount the partition
                    if mount_partition(partition, uid, gid):
                        logger.info("Successfully mounted iPod, starting sync")
                        # Sync using the mount point, not the device
                        sync_queue(MOUNT_POINT)
                    else:
                        logger.error("Failed to mount iPod partition: %s", partition)
                        
                except Exception as exc:  # pragma: no cover - runtime errors
                    logger.error("Failed to process iPod attachment: %s", exc)

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
