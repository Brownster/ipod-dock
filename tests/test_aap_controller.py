from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync.aap_controller import AAPController


def test_play_pause_frame():
    mock_serial = mock.MagicMock()
    with mock.patch('serial.Serial', return_value=mock_serial) as ser_cls:
        ctl = AAPController(port='/dev/ttyUSB1', baudrate=19200)
        ctl.play_pause()
        ser_cls.assert_called_once_with('/dev/ttyUSB1', 19200, timeout=1)
        frame = bytearray([0xFF, 0x55, 1, 0x00])
        frame.append((-sum(frame[2:])) & 0xFF)
        mock_serial.write.assert_called_once_with(frame)

