from __future__ import annotations

"""Apple Accessory Protocol (AAP) controller for iPod serial communication."""

import logging
from typing import Optional

import serial  # type: ignore

from . import config

logger = logging.getLogger(__name__)


class AAPController:
    """Manage AAP serial communication with the iPod."""

    def __init__(self, port: str | None = None, baudrate: int | None = None) -> None:
        self.port = port or config.PLAYBACK_SERIAL_PORT
        self.baudrate = baudrate or config.PLAYBACK_BAUDRATE
        self._serial: Optional[serial.Serial] = None

    def _open(self) -> serial.Serial:
        if self._serial is None or not self._serial.is_open:
            logger.debug("Opening AAP serial port %s", self.port)
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
        return self._serial

    def close(self) -> None:
        if self._serial and self._serial.is_open:
            logger.debug("Closing AAP serial port %s", self.port)
            self._serial.close()
            self._serial = None

    # Low level helpers -------------------------------------------------
    def _send(self, payload: bytes) -> None:
        """Send a raw AAP frame."""
        ser = self._open()
        frame = bytearray([0xFF, 0x55, len(payload)])
        frame.extend(payload)
        checksum = (-sum(frame[2:])) & 0xFF
        frame.append(checksum)
        logger.debug("Sending AAP frame: %s", frame.hex())
        ser.write(frame)

    def _readline(self) -> str:
        ser = self._open()
        line = ser.readline().decode(errors="ignore").strip()
        logger.debug("Received AAP line: %s", line)
        return line

    # Public API -------------------------------------------------------
    def play_pause(self) -> None:
        """Toggle playback."""
        self._send(b"\x00")

    def next_track(self) -> None:
        """Skip to the next track."""
        self._send(b"\x01")

    def previous_track(self) -> None:
        """Go to the previous track."""
        self._send(b"\x02")

    def set_volume(self, level: int) -> None:
        """Set playback volume level (0-100)."""
        level = max(0, min(100, int(level)))
        self._send(bytes([0x04, level]))

    def get_current_track_info(self) -> dict[str, str]:
        """Return the current track title/artist/album if available."""
        self._send(b"\x12")
        data = self._readline()
        parts = data.split("\t")
        return {
            "title": parts[0] if len(parts) > 0 else "",
            "artist": parts[1] if len(parts) > 1 else "",
            "album": parts[2] if len(parts) > 2 else "",
        }

    def get_playback_status(self) -> dict[str, int | str]:
        """Return basic playback status."""
        self._send(b"\x13")
        data = self._readline()
        parts = data.split(",")
        status = {
            "state": parts[0] if parts else "unknown",
            "duration": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
            "position": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
        }
        return status

    def play_track_by_id(self, db_id: int) -> None:
        """Play a track by its iTunesDB identifier."""
        db_id &= 0xFFFF
        hi = (db_id >> 8) & 0xFF
        lo = db_id & 0xFF
        self._send(bytes([0x06, hi, lo]))
