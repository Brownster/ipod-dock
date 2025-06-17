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

def test_save_to_queue_category(tmp_path):
    dest = api_helpers.save_to_queue("b.mp3", b"data", tmp_path, category="music")
    assert dest.parent.name == "music"
    assert dest.exists()


@mock.patch("ipod_sync.api_helpers.list_tracks")
@mock.patch("ipod_sync.api_helpers.eject_ipod")
@mock.patch("ipod_sync.api_helpers.mount_ipod")
def test_get_tracks_mounts_and_ejects(mock_mount, mock_eject, mock_list):
    mock_list.return_value = [{"id": "1"}]
    tracks = api_helpers.get_tracks("/dev/ipod")
    mock_mount.assert_called_once_with("/dev/ipod")
    mock_eject.assert_called_once()
    assert tracks == [{"id": "1"}]


@mock.patch("ipod_sync.api_helpers.list_playlists")
@mock.patch("ipod_sync.api_helpers.eject_ipod")
@mock.patch("ipod_sync.api_helpers.mount_ipod")
def test_get_playlists_calls_lib(mock_mount, mock_eject, mock_list):
    mock_list.return_value = [{"name": "Mix"}]
    pls = api_helpers.get_playlists("/dev/ipod")
    mock_mount.assert_called_once_with("/dev/ipod")
    mock_eject.assert_called_once()
    assert pls == [{"name": "Mix"}]


@mock.patch("ipod_sync.api_helpers.delete_track")
@mock.patch("ipod_sync.api_helpers.eject_ipod")
@mock.patch("ipod_sync.api_helpers.mount_ipod")
def test_remove_track_calls_lib(mock_mount, mock_eject, mock_delete):
    api_helpers.remove_track("42", "/dev/ipod")
    mock_mount.assert_called_once_with("/dev/ipod")
    mock_delete.assert_called_once_with("42")
    mock_eject.assert_called_once()


def test_list_and_clear_queue(tmp_path):
    file1 = tmp_path / "a.mp3"
    file1.write_bytes(b"1")
    file2 = tmp_path / "b.mp3"
    file2.write_bytes(b"2")

    files = api_helpers.list_queue(tmp_path)
    assert {f["name"] for f in files} == {"a.mp3", "b.mp3"}

    api_helpers.clear_queue(tmp_path)
    assert not any(tmp_path.iterdir())


def test_is_ipod_connected_exists(tmp_path):
    dev = tmp_path / "sda1"
    dev.write_bytes(b"")
    assert api_helpers.is_ipod_connected(str(dev))


def test_is_ipod_connected_mounts(monkeypatch):
    data = "/dev/foo /mnt/ipod vfat rw 0 0\n"
    m = mock.mock_open(read_data=data)
    monkeypatch.setattr("builtins.open", m)
    assert api_helpers.is_ipod_connected("/dev/foo")


def test_is_ipod_connected_false(monkeypatch):
    m = mock.mock_open(read_data="/dev/bar /mnt xfs rw 0 0\n")
    monkeypatch.setattr("builtins.open", m)
    assert not api_helpers.is_ipod_connected("/dev/foo")


@mock.patch("ipod_sync.api_helpers.get_tracks", return_value=[{"id": "1"}])
@mock.patch("ipod_sync.api_helpers.list_queue", return_value=[{"name": "f"}])
def test_get_stats_uses_shutil(mock_queue, mock_tracks, tmp_path):
    with mock.patch("shutil.disk_usage") as du:
        du.return_value = mock.Mock(total=100, used=25)
        stats = api_helpers.get_stats("/dev/ipod", tmp_path)
    assert stats["music"] == 1
    assert stats["podcasts"] == 0
    assert stats["queue"] == 1
    assert stats["storage_used"] == 25


@mock.patch("ipod_sync.api_helpers.create_playlist")
@mock.patch("ipod_sync.api_helpers.eject_ipod")
@mock.patch("ipod_sync.api_helpers.mount_ipod")
def test_create_new_playlist(mock_mount, mock_eject, mock_create):
    api_helpers.create_new_playlist("Mix", ["1"], "/dev/ipod")
    mock_mount.assert_called_once_with("/dev/ipod")
    mock_create.assert_called_once_with("Mix", ["1"])
    mock_eject.assert_called_once()
