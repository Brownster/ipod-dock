from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync import api_helpers


def test_save_to_queue_writes_file(tmp_path):
    dest = api_helpers.save_to_queue("a.mp3", b"data", tmp_path)
    assert dest.exists()
    assert dest.read_bytes() == b"data"


@mock.patch("ipod_sync.api_helpers.list_tracks")
@mock.patch("ipod_sync.api_helpers.eject_ipod")
@mock.patch("ipod_sync.api_helpers.mount_ipod")
def test_get_tracks_mounts_and_ejects(mock_mount, mock_eject, mock_list):
    mock_list.return_value = [{"id": "1"}]
    tracks = api_helpers.get_tracks("/dev/ipod")
    mock_mount.assert_called_once_with("/dev/ipod")
    mock_eject.assert_called_once()
    assert tracks == [{"id": "1"}]


@mock.patch("ipod_sync.api_helpers.delete_track")
@mock.patch("ipod_sync.api_helpers.eject_ipod")
@mock.patch("ipod_sync.api_helpers.mount_ipod")
def test_remove_track_calls_lib(mock_mount, mock_eject, mock_delete):
    api_helpers.remove_track("42", "/dev/ipod")
    mock_mount.assert_called_once_with("/dev/ipod")
    mock_delete.assert_called_once_with("42")
    mock_eject.assert_called_once()
