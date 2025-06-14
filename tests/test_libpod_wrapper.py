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


class FakePlaylist:
    def __init__(self, name):
        self.name = name
        self.tracks = []

    def add_track(self, track):
        self.tracks.append(track)


class FakeDatabase:
    def __init__(self):
        self.tracks = []
        self.playlists = []
        self.new_track_called_with = None
        self.new_playlist_called_with = None
        self.copy_called = False
        self.closed = False

    def new_track(self, path):
        self.new_track_called_with = path
        return FakeTrack(path)

    def add_track(self, track):
        self.tracks.append(track)

    def new_playlist(self, name):
        self.new_playlist_called_with = name
        return FakePlaylist(name)

    def add_playlist(self, playlist):
        self.playlists.append(playlist)

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


def test_list_playlists(tmp_path):
    fake = FakeGpod()
    pl = FakePlaylist("Mix")
    track = FakeTrack("/file", dbid="1")
    pl.add_track(track)
    fake.db.playlists.append(pl)
    mount = tmp_path / "mnt"
    mount.mkdir()
    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        playlists = wrapper.list_playlists()
        assert playlists == [{"name": "Mix", "tracks": ["1"]}]
        assert fake.db.closed


def test_create_playlist(tmp_path):
    fake = FakeGpod()
    track = FakeTrack("/file", dbid="1")
    fake.db.tracks.append(track)
    mount = tmp_path / "mnt"
    mount.mkdir()
    with mock.patch.object(wrapper, "gpod", fake), \
         mock.patch.object(wrapper, "IPOD_MOUNT", mount):
        wrapper.create_playlist("MyList", ["1"])
        assert fake.db.new_playlist_called_with == "MyList"
        assert fake.db.playlists[0].tracks == [track]
        assert fake.db.copy_called
        assert fake.db.closed
