from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ipod_sync.udev_listener as listener


class FakeMonitor:
    def __init__(self, events):
        self._events = events

    def __iter__(self):
        for event in self._events:
            yield event


class DummyDev(dict):
    def __init__(
        self,
        node="/dev/sda2",
        vendor="05ac",
        product="1209",
        serial="123",
        fstype="vfat",
        dtype="partition",
    ):
        super().__init__({
            "ID_VENDOR_ID": vendor,
            "ID_MODEL_ID": product,
            "ID_SERIAL_SHORT": serial,
            "ID_FS_TYPE": fstype,
        })
        self.device_node = node
        self.device_type = dtype


def _device(**kwargs):
    return DummyDev(**kwargs)


def test_listener_triggers_sync():
    monitor = FakeMonitor([("add", _device())])
    with mock.patch.object(listener, "sync_queue") as mock_sync:
        listener.listen("/dev/ipod", "05ac", "1209", monitor=monitor)
        mock_sync.assert_called_once_with("/dev/ipod")


def test_listener_auto_detects_device():
    dev = _device(node="/dev/sdx2")
    monitor = FakeMonitor([("add", dev)])
    with mock.patch.object(listener.utils, "detect_ipod_device") as det:
        with mock.patch.object(listener, "sync_queue") as mock_sync:
            listener.listen(None, "05ac", "1209", monitor=monitor)
            det.assert_not_called()
            mock_sync.assert_called_once_with("/dev/sdx2")


def test_listener_ignores_non_matching():
    monitor = FakeMonitor([("add", _device(vendor="abcd"))])
    with mock.patch.object(listener, "sync_queue") as mock_sync:
        listener.listen("/dev/ipod", monitor=monitor)
        mock_sync.assert_not_called()


def test_main_parses_args(monkeypatch):
    called = {}

    def fake_listen(device, vendor, product):
        called["args"] = (device, vendor, product)

    monkeypatch.setattr(listener, "listen", fake_listen)
    monkeypatch.setattr(listener, "setup_logging", lambda: None)

    listener.main(["--device", "/dev/x", "--vendor", "1111", "--product", "2222"])

    assert called["args"] == ("/dev/x", "1111", "2222")
