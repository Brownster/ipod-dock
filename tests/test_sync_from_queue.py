import sys
from pathlib import Path
from unittest import mock
import logging

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync import sync_from_queue


@mock.patch("ipod_sync.sync_from_queue.get_ipod_repo")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_queue_processes_files(mock_mount, mock_eject, mock_prepare, mock_repo_factory, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    f1 = queue / "a.mp3"
    f1.write_text("a")
    f2 = queue / "b.mp3"
    f2.write_text("b")

    # Mock repository
    mock_repo = mock.Mock()
    mock_repo.add_track.return_value = "track_id_123"
    mock_repo_factory.return_value = mock_repo

    with mock.patch("ipod_sync.config.config_manager.config.sync_queue_dir", queue), \
         mock.patch("ipod_sync.config.config_manager.config.keep_local_copy", False):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_mount.assert_called_once_with("/dev/ipod")
    mock_eject.assert_called_once()
    mock_prepare.assert_has_calls([mock.call(f1), mock.call(f2)], any_order=True)
    assert mock_repo.add_track.call_count == 2
    assert not any(queue.iterdir())


@mock.patch("ipod_sync.sync_from_queue.get_ipod_repo")
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_queue_no_files(mock_mount, mock_eject, mock_repo_factory, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()

    with mock.patch("ipod_sync.config.config_manager.config.sync_queue_dir", queue):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_mount.assert_not_called()
    mock_eject.assert_not_called()
    mock_repo_factory.assert_not_called()


@mock.patch("ipod_sync.sync_from_queue.get_ipod_repo")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_keep_local_copy(mock_mount, mock_eject, mock_prepare, mock_repo_factory, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    file_path = queue / "song.mp3"
    file_path.write_text("x")

    # Mock repository
    mock_repo = mock.Mock()
    mock_repo.add_track.return_value = "track_id_123"
    mock_repo_factory.return_value = mock_repo

    with mock.patch("ipod_sync.config.config_manager.config.sync_queue_dir", queue), \
         mock.patch("ipod_sync.config.config_manager.config.keep_local_copy", True):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_prepare.assert_called_once_with(file_path)
    assert file_path.exists()


@mock.patch("ipod_sync.sync_from_queue.get_ipod_repo")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_recurses_subdirs(mock_mount, mock_eject, mock_prepare, mock_repo_factory, tmp_path):
    queue = tmp_path / "queue"
    sub = queue / "podcast"
    sub.mkdir(parents=True)
    f = sub / "ep.mp3"
    f.write_text("x")

    # Mock repository
    mock_repo = mock.Mock()
    mock_repo.add_track.return_value = "track_id_123"
    mock_repo_factory.return_value = mock_repo

    with mock.patch("ipod_sync.config.config_manager.config.sync_queue_dir", queue), \
         mock.patch("ipod_sync.config.config_manager.config.keep_local_copy", False):
        sync_from_queue.sync_queue("/dev/ipod")

    mock_prepare.assert_called_once_with(f)
    mock_repo.add_track.assert_called_once()


@mock.patch("ipod_sync.sync_from_queue.get_ipod_repo")
@mock.patch("ipod_sync.sync_from_queue.converter.prepare_for_sync", side_effect=lambda p: p)
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_error_logged(mock_mount, mock_eject, mock_prepare, mock_repo_factory, caplog, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    f = queue / "err.mp3"
    f.write_text("x")

    # Mock repository that raises error
    mock_repo = mock.Mock()
    mock_repo.add_track.side_effect = RuntimeError("boom")
    mock_repo_factory.return_value = mock_repo

    with mock.patch("ipod_sync.config.config_manager.config.sync_queue_dir", queue), \
         mock.patch("ipod_sync.config.config_manager.config.keep_local_copy", False):
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
