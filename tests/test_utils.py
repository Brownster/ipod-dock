import sys
from pathlib import Path
from unittest import mock
import subprocess
import logging
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
    with mock.patch("ipod_sync.config.config_manager.config.ipod.mount_point", mount_point), \
         mock.patch("ipod_sync.config.config_manager.config.project_root", tmp_path), \
         mock.patch.object(utils, "wait_for_device", return_value=True), \
         mock.patch("os.geteuid", return_value=1000):
        utils.mount_ipod(str(device))
        mount_call = mock.call(
            [
                "sudo",
                "--non-interactive",
                "--",
                utils.MOUNT_BIN,
                "-t",
                "vfat",
                "--",
                str(device),
                str(mount_point),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert mount_call in mock_run.call_args_list
        assert mount_point.exists()
        assert (tmp_path / "ipod_status").read_text() == "true"


@mock.patch("ipod_sync.utils.subprocess.run")
def test_mount_ipod_waits_for_label(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    status = tmp_path / "status"
    device = tmp_path / "sdb2"
    device.write_text("")

    with mock.patch("ipod_sync.config.config_manager.config.ipod.mount_point", mount_point), \
         mock.patch("ipod_sync.config.config_manager.config.project_root", tmp_path), \
         mock.patch.object(utils, "wait_for_device", return_value=True), \
         mock.patch.object(utils, "wait_for_label", return_value=device) as wfl, \
         mock.patch("os.geteuid", return_value=1000):
        utils.mount_ipod(None)  # Will use default device path
        wfl.assert_called_once()
        mount_call = mock.call(
            [
                "sudo",
                "--non-interactive",
                "--",
                utils.MOUNT_BIN,
                "-t",
                "vfat",
                "--",
                str(device),
                str(mount_point),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert mount_call in mock_run.call_args_list


@mock.patch("ipod_sync.utils.subprocess.run")
def test_mount_ipod_label_missing_auto_detect(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    status = tmp_path / "status"
    device = tmp_path / "sdc1"
    device.write_text("")

    with mock.patch("ipod_sync.config.config_manager.config.ipod.mount_point", mount_point), \
         mock.patch("ipod_sync.config.config_manager.config.project_root", tmp_path), \
         mock.patch.object(utils, "wait_for_device", return_value=True), \
         mock.patch.object(utils, "wait_for_label", side_effect=FileNotFoundError), \
         mock.patch.object(utils, "detect_ipod_device", return_value=str(device)) as detect, \
         mock.patch("os.geteuid", return_value=1000):
        utils.mount_ipod(None)  # Will use default device path
        detect.assert_called_once()
        mount_call = mock.call(
            [
                "sudo",
                "--non-interactive",
                "--",
                utils.MOUNT_BIN,
                "-t",
                "vfat",
                "--",
                str(device),
                str(mount_point),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert mount_call in mock_run.call_args_list


@mock.patch("ipod_sync.utils.subprocess.run")
def test_eject_ipod_calls_umount_and_eject(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    mount_point = tmp_path / "mnt"
    status = tmp_path / "status"
    status.write_text("true")
    with mock.patch("ipod_sync.config.config_manager.config.ipod.mount_point", mount_point), \
         mock.patch("ipod_sync.config.config_manager.config.project_root", tmp_path), \
         mock.patch("os.geteuid", return_value=1000), \
         mock.patch("os.path.ismount", return_value=True):
        utils.eject_ipod()
        mock_run.assert_has_calls(
            [
                mock.call(
                    [
                        "findmnt",
                        "-n",
                        "-o",
                        "SOURCE",
                        str(mount_point),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ),
                mock.call(
                    [
                        "sudo",
                        "--non-interactive",
                        "--",
                        "umount",
                        str(mount_point),
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
                mock.call(
                    [
                        "sudo",
                        "--non-interactive",
                        "--",
                        "eject",
                        str(mount_point),
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
            ]
        )
        assert not (tmp_path / "ipod_status").exists()


@mock.patch("ipod_sync.utils.subprocess.run")
def test_eject_ipod_skips_when_not_mounted(mock_run, tmp_path):
    mount_point = tmp_path / "mnt"
    status = tmp_path / "status"
    status.write_text("true")
    with mock.patch("ipod_sync.config.config_manager.config.ipod.mount_point", mount_point), \
         mock.patch("ipod_sync.config.config_manager.config.project_root", tmp_path), \
         mock.patch("os.path.ismount", return_value=False):
        utils.eject_ipod()
    mock_run.assert_not_called()
    assert not (tmp_path / "ipod_status").exists()


@mock.patch("ipod_sync.utils.subprocess.run")
def test_run_raises_on_error(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(["cmd"], 1, "", "fail")
    with pytest.raises(subprocess.CalledProcessError) as exc:
        utils._run(["cmd"], capture_output=True)
    assert exc.value.stderr == "fail"


@mock.patch("ipod_sync.utils.subprocess.run")
def test_run_uses_sudo_when_requested(mock_run):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    with mock.patch("os.geteuid", return_value=1000):
        utils._run(["echo", "hi"], use_sudo=True)
    mock_run.assert_called_with(
        ["sudo", "--non-interactive", "--", "echo", "hi"],
        check=False,
        stderr=subprocess.PIPE,
        text=True,
    )


@mock.patch("ipod_sync.utils.subprocess.run")
def test_mount_ipod_reports_sudo_password_error(mock_run, tmp_path, caplog):
    mock_run.return_value = subprocess.CompletedProcess([], 1, "", "sudo: a password is required")
    mount_point = tmp_path / "mnt"
    device = tmp_path / "sdb1"
    device.write_text("")
    caplog.set_level(logging.ERROR)
    with mock.patch("ipod_sync.config.config_manager.config.ipod.mount_point", mount_point), \
         mock.patch("ipod_sync.config.config_manager.config.project_root", tmp_path), \
         mock.patch.object(utils, "wait_for_device", return_value=True), \
         mock.patch("os.geteuid", return_value=1000):
        utils.mount_ipod(str(device))
    assert any("sudo requires a password" in r.message for r in caplog.records)


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
    with mock.patch("ipod_sync.config.config_manager.config.ipod.device_path", "/dev/foo"):
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
    monkeypatch.setattr(utils, "_run", lambda cmd, **kw: None)
    monkeypatch.setattr("ipod_sync.config.config_manager.config.ipod.mount_point", Path("/tmp/mnt"))
    monkeypatch.setattr(utils, "wait_for_device", lambda p, t=5.0: True)

    utils.mount_ipod(None)
    assert called["called"]
