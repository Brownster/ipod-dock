import sys
from pathlib import Path
from unittest import mock
import logging

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync import sync_from_queue


@mock.patch("ipod_sync.sync_from_queue.add_track")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_queue_processes_files(mock_mount, mock_eject, mock_prepare, mock_add, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    f1 = queue / "a.mp3"
    f1.write_text("a")
    f2 = queue / "b.mp3"
    f2.write_text("b")

    with mock.patch.object(sync_from_queue, "config", mock.Mock(SYNC_QUEUE_DIR=queue, IPOD_DEVICE="/dev/ipod", KEEP_LOCAL_COPY=False)):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_mount.assert_called_once_with("/dev/ipod")
    mock_eject.assert_called_once()
    mock_prepare.assert_has_calls([mock.call(f1), mock.call(f2)], any_order=True)
    mock_add.assert_has_calls([mock.call(f1), mock.call(f2)], any_order=True)
    assert not any(queue.iterdir())


@mock.patch("ipod_sync.sync_from_queue.add_track")
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_queue_no_files(mock_mount, mock_eject, mock_add, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()

    with mock.patch.object(sync_from_queue, "config", mock.Mock(SYNC_QUEUE_DIR=queue, IPOD_DEVICE="/dev/ipod", KEEP_LOCAL_COPY=False)):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_mount.assert_not_called()
    mock_eject.assert_not_called()
    mock_add.assert_not_called()


@mock.patch("ipod_sync.sync_from_queue.add_track")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_keep_local_copy(mock_mount, mock_eject, mock_prepare, mock_add, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    file_path = queue / "song.mp3"
    file_path.write_text("x")

    with mock.patch.object(sync_from_queue, "config", mock.Mock(SYNC_QUEUE_DIR=queue, IPOD_DEVICE="/dev/ipod", KEEP_LOCAL_COPY=True)):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_prepare.assert_called_once_with(file_path)
    assert file_path.exists()


@mock.patch("ipod_sync.sync_from_queue.add_track")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_recurses_subdirs(mock_mount, mock_eject, mock_prepare, mock_add, tmp_path):
    queue = tmp_path / "queue"
    sub = queue / "podcast"
    sub.mkdir(parents=True)
    f = sub / "ep.mp3"
    f.write_text("x")

    with mock.patch.object(sync_from_queue, "config", mock.Mock(SYNC_QUEUE_DIR=queue, IPOD_DEVICE="/dev/ipod", KEEP_LOCAL_COPY=False)):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_prepare.assert_called_once_with(f)
    mock_add.assert_called_once_with(f)


@mock.patch("ipod_sync.sync_from_queue.add_track", side_effect=RuntimeError("boom"))
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_error_logged(mock_mount, mock_eject, mock_prepare, mock_add, caplog, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    f = queue / "err.mp3"
    f.write_text("x")

    with mock.patch.object(sync_from_queue, "config", mock.Mock(SYNC_QUEUE_DIR=queue, IPOD_DEVICE="/dev/ipod", KEEP_LOCAL_COPY=False)):
        with caplog.at_level(logging.ERROR):
            sync_from_queue.sync_queue("/dev/ipod")
        assert "Failed to sync" in caplog.text
    mock_prepare.assert_called_once_with(f)


def test_cli_main(monkeypatch):
    called = {}

    def fake_sync(device):
        called['device'] = device

    monkeypatch.setattr(sync_from_queue, 'sync_queue', fake_sync)
    sync_from_queue.main(['--device', '/dev/x'])
    assert called['device'] == '/dev/x'
