import sys
from pathlib import Path
from unittest import mock
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ipod_sync.libpod_wrapper as wrapper


class FakeTrack:
    def __init__(self, path, dbid="1"):
        self.path = path
        self.dbid = dbid
        self.title = "Test"
        self.artist = "Artist"
        self.album = "Album"


class FakeDatabase:
    def __init__(self):
        self.tracks = []
        self.new_track_called_with = None
        self.copy_called = False
        self.closed = False

    def new_track(self, path):
        self.new_track_called_with = path
        return FakeTrack(path)

    def add_track(self, track):
        self.tracks.append(track)

    def copy_delayed_files(self):
        self.copy_called = True

    def close(self):
        self.closed = True

    def remove_track(self, track):
        self.tracks.remove(track)


class FakeGpod:
    def __init__(self):
        self.db = FakeDatabase()
        self.database_called_with = None

    def Database(self, path):
        self.database_called_with = path
        return self.db


def test_add_track_invokes_gpod(tmp_path):
    fake = FakeGpod()
    file_path = tmp_path / "song.mp3"
    file_path.write_text("data")
    mount = tmp_path / "mnt"
    mount.mkdir()

    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        wrapper.add_track(file_path)
        assert fake.database_called_with == str(mount)
        assert fake.db.new_track_called_with == str(file_path)
        assert fake.db.copy_called
        assert fake.db.closed


def test_delete_track_removes_from_db(tmp_path):
    fake = FakeGpod()
    track = FakeTrack("/file")
    fake.db.tracks.append(track)
    mount = tmp_path / "mnt"
    mount.mkdir()

    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        wrapper.delete_track(track.dbid)
        assert track not in fake.db.tracks
        assert fake.db.copy_called
        assert fake.db.closed


def test_list_tracks_returns_metadata(tmp_path):
    fake = FakeGpod()
    fake.db.tracks.append(FakeTrack("/file", dbid="42"))
    mount = tmp_path / "mnt"
    mount.mkdir()

    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        tracks = wrapper.list_tracks()
        assert tracks == [{"id": "42", "title": "Test", "artist": "Artist", "album": "Album"}]
        assert fake.db.closed


def test_add_track_missing_file(tmp_path):
    fake = FakeGpod()
    mount = tmp_path / "mnt"
    mount.mkdir()
    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        with pytest.raises(FileNotFoundError):
            wrapper.add_track(tmp_path / "missing.mp3")


def test_error_if_bindings_missing(tmp_path):
    with mock.patch.object(wrapper, "gpod", None):
        with pytest.raises(RuntimeError):
            wrapper.list_tracks()


def test_delete_track_not_found(tmp_path):
    fake = FakeGpod()
    mount = tmp_path / "mnt"
    mount.mkdir()
    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        with pytest.raises(KeyError):
            wrapper.delete_track("99")
