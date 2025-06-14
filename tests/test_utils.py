import sys
from pathlib import Path
from unittest import mock
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ipod_sync.utils as utils


@mock.patch("ipod_sync.utils.subprocess.run")
def test_mount_ipod_calls_mount(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    device = "/dev/sdb1"
    with mock.patch.object(utils, "IPOD_MOUNT", mount_point):
        utils.mount_ipod(device)
        mock_run.assert_called_with(
            ["mount", device, str(mount_point)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert mount_point.exists()


@mock.patch("ipod_sync.utils.subprocess.run")
def test_eject_ipod_calls_umount_and_eject(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    with mock.patch.object(utils, "IPOD_MOUNT", mount_point):
        utils.eject_ipod()
        mock_run.assert_has_calls(
            [
                mock.call([
                    "umount",
                    str(mount_point),
                ], check=True, capture_output=True, text=True),
                mock.call([
                    "eject",
                    str(mount_point),
                ], check=True, capture_output=True, text=True),
            ]
        )
