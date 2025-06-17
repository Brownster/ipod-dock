"""Listen for iPod USB events and trigger syncing."""

from __future__ import annotations

import argparse
import logging
from typing import Iterable, Tuple

import pyudev

from . import config
from .logging_setup import setup_logging
from .sync_from_queue import sync_queue

logger = logging.getLogger(__name__)


def listen(
    device: str = config.IPOD_DEVICE,
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
    for action, dev in monitor:
        if (
            dev.get("ID_VENDOR_ID") == vendor
            and dev.get("ID_MODEL_ID") == product
        ):
            serial = dev.get("ID_SERIAL_SHORT", "unknown")
            logger.debug("Event %s for %s", action, serial)
            if action == "add":
                logger.info("iPod %s attached", serial)
                try:
                    sync_queue(device)
                except Exception as exc:  # pragma: no cover - runtime errors
                    logger.error("Failed to sync: %s", exc)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Listen for iPod USB events")
    parser.add_argument(
        "--device",
        default=config.IPOD_DEVICE,
        help="Path to iPod block device",
    )
    parser.add_argument("--vendor", default="05ac", help="USB vendor ID")
    parser.add_argument("--product", default="1209", help="USB product ID")
    args = parser.parse_args(argv)

    setup_logging()
    listen(args.device, args.vendor, args.product)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
