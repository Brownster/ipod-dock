"""Listen for iPod USB events and trigger syncing."""

from __future__ import annotations

import argparse
import logging
from typing import Iterable, Tuple

import pyudev

from . import config, utils
from pathlib import Path
from .logging_setup import setup_logging
from .sync_from_queue import sync_queue

# Path used to indicate connection status to other components
STATUS_FILE = Path(config.IPOD_STATUS_FILE)

logger = logging.getLogger(__name__)


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
    """Listen for matching USB device events and sync on attach.

    If *device* is ``None`` the FAT partition is detected automatically when the
    iPod is connected.
    """
    if monitor is None:
        ctx = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(ctx)
        monitor.filter_by("block")
        monitor = iter(monitor)

    logger.info("Listening for iPod USB events")
    _set_connected(False)
    for action, dev in monitor:
        if (
            dev.get("ID_VENDOR_ID") == vendor
            and dev.get("ID_MODEL_ID") == product
        ):
            serial = dev.get("ID_SERIAL_SHORT", "unknown")
            logger.debug("Event %s for %s", action, serial)
            if action == "add" and dev.device_type == "partition" and dev.get("ID_FS_TYPE") == "vfat":
                logger.info("iPod %s attached", serial)
                _set_connected(True)
                try:
                    dev_path = device if device is not None else dev.device_node
                    sync_queue(dev_path)
                except Exception as exc:  # pragma: no cover - runtime errors
                    logger.error("Failed to sync: %s", exc)
            elif action == "remove" and dev.device_type == "disk":
                logger.info("iPod %s removed", serial)
                _set_connected(False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Listen for iPod USB events")
    parser.add_argument(
        "--device",
        default=None,
        help="Path to iPod block device (auto-detect if omitted)",
    )
    parser.add_argument("--vendor", default="05ac", help="USB vendor ID")
    parser.add_argument("--product", default="1209", help="USB product ID")
    args = parser.parse_args(argv)

    setup_logging()
    listen(args.device, args.vendor, args.product)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
