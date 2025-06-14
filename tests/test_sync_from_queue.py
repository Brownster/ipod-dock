import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync import sync_from_queue


@mock.patch("ipod_sync.sync_from_queue.add_track")
@mock.patch("ipod_sync.sync_from_queue.eject_ipod")
@mock.patch("ipod_sync.sync_from_queue.mount_ipod")
def test_sync_queue_processes_files(mock_mount, mock_eject, mock_add, tmp_path):
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
