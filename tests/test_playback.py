import types
from unittest import mock

from ipod_sync.playback import SerialPlayback


def test_send_play_command():
    mock_serial = mock.MagicMock()
    with mock.patch('serial.Serial', return_value=mock_serial) as ser_cls:
        ctl = SerialPlayback(port='/dev/ttyUSB0', baudrate=19200)
        ctl.play_pause()
        ser_cls.assert_called_once_with('/dev/ttyUSB0', 19200, timeout=1)
        frame = bytearray([0xFF, 0x55, 0x03, 0x00, 0x00, 0x00])
        frame.append((-sum(frame[2:])) & 0xFF)
        mock_serial.write.assert_called_once_with(frame)

