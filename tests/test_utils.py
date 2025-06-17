import sys
from pathlib import Path
from unittest import mock
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ipod_sync.utils as utils


@mock.patch("ipod_sync.utils.subprocess.run")
def test_mount_ipod_calls_mount(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    status = tmp_path / "status"
    device = tmp_path / "sdb1"
    device.write_text("")
    with mock.patch.object(utils, "IPOD_MOUNT", mount_point), mock.patch.object(
        utils, "IPOD_STATUS_FILE", status
    ), mock.patch.object(utils, "wait_for_device", return_value=True):
        utils.mount_ipod(str(device))
        mock_run.assert_called_with(
            ["mount", "-t", "vfat", str(device), str(mount_point)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert mount_point.exists()
        assert status.read_text() == "true"


@mock.patch("ipod_sync.utils.subprocess.run")
def test_eject_ipod_calls_umount_and_eject(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    status = tmp_path / "status"
    status.write_text("true")
    with mock.patch.object(utils, "IPOD_MOUNT", mount_point), mock.patch.object(
        utils, "IPOD_STATUS_FILE", status
    ):
        utils.eject_ipod()
        mock_run.assert_has_calls(
            [
                mock.call(
                    [
                        "umount",
                        str(mount_point),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ),
                mock.call(
                    [
                        "eject",
                        str(mount_point),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ),
            ]
        )
        assert not status.exists()


@mock.patch("ipod_sync.utils.subprocess.run")
def test_run_raises_on_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"], "", "fail")
    with pytest.raises(RuntimeError):
        utils._run(["cmd"])


@mock.patch("ipod_sync.utils.subprocess.run")
def test_detect_ipod_device_parses_lsblk(mock_run):
    output = (
        '{"blockdevices": ['
        '{"name": "sda", "children": ['
        '{"name": "sda1", "fstype": "hfs", "size": "100"},'
        '{"name": "sda2", "fstype": "vfat", "size": "200"}'
        "]}]}"
    )
    mock_run.return_value = subprocess.CompletedProcess([], 0, output, "")
    dev = utils.detect_ipod_device()
    assert dev == "/dev/sda2"


@mock.patch("ipod_sync.utils.subprocess.run", side_effect=FileNotFoundError)
def test_detect_ipod_device_fallback(mock_run):
    with mock.patch.object(utils, "IPOD_DEVICE", "/dev/foo"):
        dev = utils.detect_ipod_device()
    assert dev == "/dev/foo"


def test_mount_ipod_auto_detect(monkeypatch, tmp_path):
    called = {}

    dev = tmp_path / "ipod"
    dev.write_text("")

    def fake_detect():
        called["called"] = True
        return str(dev)

    monkeypatch.setattr(utils, "detect_ipod_device", fake_detect)
    monkeypatch.setattr(utils, "_run", lambda cmd: None)
    monkeypatch.setattr(utils, "IPOD_MOUNT", Path("/tmp/mnt"))
    monkeypatch.setattr(utils, "wait_for_device", lambda p, t=5.0: True)

    utils.mount_ipod(None)
    assert called["called"]
