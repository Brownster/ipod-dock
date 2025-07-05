from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from ipod_sync.app import app
import ipod_sync.app as app_module
from ipod_sync.repositories import Track, Playlist

client = TestClient(app)


def test_status_endpoint(monkeypatch):
    monkeypatch.setattr(app_module, "is_ipod_connected", lambda *_: True)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["connected"] is True


def test_auth_required_when_key_set(monkeypatch):
    monkeypatch.setattr(app_module.config, "API_KEY", "secret")
    monkeypatch.setattr(app_module, "is_ipod_connected", lambda *_: False)
    unauthorized = client.get("/status")
    assert unauthorized.status_code == 401
    ok = client.get("/status", headers={"X-API-Key": "secret"})
    assert ok.status_code == 200


@mock.patch("ipod_sync.routers.queue.save_to_queue")
def test_upload_endpoint(mock_save):
    mock_save.return_value = Path("sync_queue/foo.mp3")
    response = client.post(
        "/api/v1/queue/upload",
        files={"file": ("foo.mp3", b"abc")},
        params={"category": "music"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "queued": "foo.mp3", "category": "music"}
    mock_save.assert_called_once()


@mock.patch("ipod_sync.routers.queue.save_to_queue")
def test_upload_category_endpoint(mock_save):
    mock_save.return_value = Path("sync_queue/audiobook/foo.m4b")
    response = client.post(
        "/api/v1/queue/upload",
        files={"file": ("foo.m4b", b"abc")},
        params={"category": "audiobook"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "queued": "foo.m4b", "category": "audiobook"}
    mock_save.assert_called_once_with("foo.m4b", b"abc", category="audiobook")


@mock.patch("ipod_sync.routers.queue.save_to_queue")
def test_upload_podcast_category(mock_save):
    mock_save.return_value = Path("sync_queue/podcast/ep.mp3")
    response = client.post(
        "/api/v1/queue/upload",
        files={"file": ("ep.mp3", b"abc")},
        params={"category": "podcast"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "queued": "ep.mp3", "category": "podcast"}
    mock_save.assert_called_once_with("ep.mp3", b"abc", category="podcast")


def test_upload_category_invalid():
    response = client.post(
        "/api/v1/queue/upload",
        files={"file": ("foo.mp3", b"abc")},
        params={"category": "invalid"},
    )
    assert response.status_code == 400


@mock.patch('ipod_sync.routers.tracks.get_ipod_repo')
def test_tracks_endpoint(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.get_tracks.return_value = [Track(id="1", title="Song")]
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.get("/api/v1/tracks?source=ipod")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "1"
    mock_repo.get_tracks.assert_called_once()


@mock.patch('ipod_sync.routers.tracks.get_ipod_repo')
def test_tracks_endpoint_error(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.get_tracks.side_effect = RuntimeError("boom")
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.get("/api/v1/tracks?source=ipod")

    assert response.status_code == 500
    assert "boom" in response.text
    mock_repo.get_tracks.assert_called_once()


@mock.patch('ipod_sync.routers.tracks.get_ipod_repo')
def test_delete_track_endpoint(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.remove_track.return_value = True
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.delete("/api/v1/tracks/42?source=ipod")

    assert response.status_code == 200
    mock_repo.remove_track.assert_called_once_with("42")


@mock.patch('ipod_sync.routers.tracks.get_ipod_repo')
def test_delete_track_not_found(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.remove_track.return_value = False
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.delete("/api/v1/tracks/99?source=ipod")

    assert response.status_code == 404
    mock_repo.remove_track.assert_called_once_with("99")


@mock.patch('ipod_sync.routers.playlists.get_ipod_repo')
def test_playlists_get(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.get_playlists.return_value = [Playlist(id="1", name="Mix", track_ids=[])]
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.get("/api/v1/playlists")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Mix"
    mock_repo.get_playlists.assert_called_once()


@mock.patch('ipod_sync.routers.playlists.get_ipod_repo')
def test_playlists_post(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.create_playlist.return_value = "Mix"
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.post("/api/v1/playlists", json={"name": "Mix", "track_ids": ["1"]})

    assert response.status_code == 200
    assert response.json()["data"]["playlist_id"] == "Mix"
    mock_repo.create_playlist.assert_called_once_with("Mix", ["1"]) 


@mock.patch('ipod_sync.routers.queue.get_queue_repo')
def test_queue_endpoint(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_track = Track(id="1", title="a.mp3")
    mock_repo.get_tracks.return_value = [mock_track]
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.get("/api/v1/queue")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "a.mp3"
    mock_repo.get_tracks.assert_called_once()


@mock.patch('ipod_sync.routers.queue.get_queue_repo')
def test_queue_clear_endpoint(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.clear_queue.return_value = True
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.post("/api/v1/queue/clear")

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_repo.clear_queue.assert_called_once()


@mock.patch('ipod_sync.routers.control.sync_from_queue')
def test_sync_endpoint(mock_sync):
    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.post("/api/v1/control/sync")

    assert response.status_code == 200
    assert response.json()["message"]
    mock_sync.sync_queue.assert_called_once_with(app_module.config.IPOD_DEVICE)


@mock.patch('ipod_sync.routers.control.sync_from_queue')
def test_sync_endpoint_error(mock_sync):
    mock_sync.sync_queue.side_effect = RuntimeError("boom")
    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.post("/api/v1/control/sync")

    assert response.status_code == 500
    assert "boom" in response.text
    mock_sync.sync_queue.assert_called_once_with(app_module.config.IPOD_DEVICE)




@mock.patch('ipod_sync.routers.tracks.get_ipod_repo')
def test_stats_endpoint(mock_repo_factory):
    mock_repo = mock.MagicMock()
    mock_repo.get_stats.return_value = {
        "total_tracks": 1,
        "total_duration_seconds": 60,
        "total_size_bytes": 1234,
        "categories": {"music": 1},
        "total_playlists": 0,
    }
    mock_repo_factory.return_value = mock_repo

    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.get("/api/v1/tracks/stats/summary?source=ipod")

    assert response.status_code == 200
    data = response.json()
    assert data["total_tracks"] == 1
    assert data["categories"]["music"] == 1
    mock_repo.get_stats.assert_called_once()


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>iPod Dock</title>" in response.text


def test_audible_page():
    response = client.get("/audible")
    assert response.status_code == 404


@mock.patch('ipod_sync.routers.control.playback_controller')
def test_control_endpoint(mock_ctl):
    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.post("/api/v1/control/playback/play")

    assert response.status_code == 200
    mock_ctl.play_pause.assert_called_once()


@mock.patch('ipod_sync.routers.control.playback_controller')
def test_control_invalid(mock_ctl):
    with mock.patch('ipod_sync.auth.verify_api_key', return_value=None):
        response = client.post("/api/v1/control/playback/boom")

    assert response.status_code == 400
    mock_ctl.play_pause.assert_not_called()


