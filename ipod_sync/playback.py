"""Simple serial-based playback control for the iPod dock."""

from __future__ import annotations

import logging
from typing import Optional

import serial  # type: ignore

from .config import config_manager

logger = logging.getLogger(__name__)


class SerialPlayback:
    """Send basic playback commands over the dock serial pins."""

    def __init__(self, port: str | None = None, baudrate: int | None = None) -> None:
        self.port = port or config_manager.config.serial.port
        self.baudrate = baudrate or config_manager.config.serial.baudrate
        self._serial: Optional[serial.Serial] = None

    def _open(self) -> serial.Serial:
        if self._serial is None or not self._serial.is_open:
            logger.debug("Opening serial port %s", self.port)
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
        return self._serial

    def _send(self, command: int, param1: int = 0x00, param2: int = 0x00) -> None:
        ser = self._open()
        frame = bytearray([0xFF, 0x55, 0x03, command & 0xFF, param1 & 0xFF, param2 & 0xFF])
        checksum = (-sum(frame[2:])) & 0xFF
        frame.append(checksum)
        logger.debug("Sending frame: %s", frame.hex())
        ser.write(frame)

    def play_pause(self) -> None:
        """Toggle play/pause on the iPod."""
        self._send(0x00)

    def next_track(self) -> None:
        """Skip to the next track."""
        self._send(0x01)

    def prev_track(self) -> None:
        """Go to the previous track."""
        self._send(0x02)

    def close(self) -> None:
        if self._serial and self._serial.is_open:
            logger.debug("Closing serial port %s", self.port)
            self._serial.close()
            self._serial = None
