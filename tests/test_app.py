from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from ipod_sync.app import app
import ipod_sync.app as app_module

client = TestClient(app)


def test_status_endpoint(monkeypatch):
    monkeypatch.setattr(app_module, "is_ipod_connected", lambda *_: True)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "connected": True}


def test_auth_required_when_key_set(monkeypatch):
    monkeypatch.setattr(app_module.config, "API_KEY", "secret")
    monkeypatch.setattr(app_module, "is_ipod_connected", lambda *_: False)
    unauthorized = client.get("/status")
    assert unauthorized.status_code == 401
    ok = client.get("/status", headers={"X-API-Key": "secret"})
    assert ok.status_code == 200


@mock.patch.object(app_module, "save_to_queue")
def test_upload_endpoint(mock_save):
    mock_save.return_value = Path("sync_queue/foo.mp3")
    response = client.post("/upload", files={"file": ("foo.mp3", b"abc")})
    assert response.status_code == 200
    assert response.json() == {"queued": "foo.mp3"}
    mock_save.assert_called_once()


@mock.patch.object(app_module, "save_to_queue")
def test_upload_category_endpoint(mock_save):
    mock_save.return_value = Path("sync_queue/audiobook/foo.m4b")
    response = client.post("/upload/audiobook", files={"file": ("foo.m4b", b"abc")})
    assert response.status_code == 200
    assert response.json() == {"queued": "foo.m4b", "category": "audiobook"}
    mock_save.assert_called_once_with("foo.m4b", b"abc", category="audiobook")


@mock.patch.object(app_module, "save_to_queue")
def test_upload_podcast_category(mock_save):
    mock_save.return_value = Path("sync_queue/podcast/ep.mp3")
    response = client.post("/upload/podcast", files={"file": ("ep.mp3", b"abc")})
    assert response.status_code == 200
    assert response.json() == {"queued": "ep.mp3", "category": "podcast"}
    mock_save.assert_called_once_with("ep.mp3", b"abc", category="podcast")


def test_upload_category_invalid():
    response = client.post("/upload/invalid", files={"file": ("foo.mp3", b"abc")})
    assert response.status_code == 400


@mock.patch.object(app_module, "get_tracks", return_value=[{"id": "1"}])
def test_tracks_endpoint(mock_get):
    response = client.get("/tracks")
    assert response.status_code == 200
    assert response.json() == [{"id": "1"}]
    mock_get.assert_called_once()


@mock.patch.object(app_module, "get_tracks", side_effect=RuntimeError("boom"))
def test_tracks_endpoint_error(mock_get):
    response = client.get("/tracks")
    assert response.status_code == 500
    assert "boom" in response.text
    mock_get.assert_called_once()


@mock.patch.object(app_module, "remove_track")
def test_delete_track_endpoint(mock_remove):
    response = client.delete("/tracks/42")
    assert response.status_code == 200
    assert response.json() == {"deleted": "42"}
    mock_remove.assert_called_once_with("42", app_module.config.IPOD_DEVICE)


@mock.patch.object(app_module, "remove_track", side_effect=KeyError)
def test_delete_track_not_found(mock_remove):
    response = client.delete("/tracks/99")
    assert response.status_code == 404
    mock_remove.assert_called_once_with("99", app_module.config.IPOD_DEVICE)


@mock.patch.object(app_module, "get_playlists", return_value=[{"name": "Mix"}])
def test_playlists_get(mock_get):
    response = client.get("/playlists")
    assert response.status_code == 200
    assert response.json() == [{"name": "Mix"}]
    mock_get.assert_called_once_with(app_module.config.IPOD_DEVICE)


@mock.patch.object(app_module, "create_new_playlist")
def test_playlists_post(mock_create):
    response = client.post("/playlists", json={"name": "Mix", "tracks": ["1"]})
    assert response.status_code == 200
    assert response.json() == {"created": "Mix"}
    mock_create.assert_called_once_with("Mix", ["1"], app_module.config.IPOD_DEVICE)


@mock.patch.object(app_module, "list_queue", return_value=[{"name": "a.mp3"}])
def test_queue_endpoint(mock_list):
    response = client.get("/queue")
    assert response.status_code == 200
    assert response.json() == [{"name": "a.mp3"}]
    mock_list.assert_called_once()


@mock.patch.object(app_module, "clear_queue")
def test_queue_clear_endpoint(mock_clear):
    response = client.post("/queue/clear")
    assert response.status_code == 200
    assert response.json() == {"cleared": True}
    mock_clear.assert_called_once()


@mock.patch.object(app_module, "sync_from_queue")
def test_sync_endpoint(mock_sync):
    response = client.post("/sync")
    assert response.status_code == 200
    assert response.json() == {"synced": True}
    mock_sync.sync_queue.assert_called_once_with(app_module.config.IPOD_DEVICE)


@mock.patch.object(app_module, "sync_from_queue")
def test_sync_endpoint_error(mock_sync):
    mock_sync.sync_queue.side_effect = RuntimeError("boom")
    response = client.post("/sync")
    assert response.status_code == 500
    assert "boom" in response.text
    mock_sync.sync_queue.assert_called_once_with(app_module.config.IPOD_DEVICE)


@mock.patch.object(app_module, "podcast_fetcher")
def test_podcasts_fetch_endpoint(mock_fetcher):
    mock_fetcher.fetch_podcasts.return_value = [Path("sync_queue/podcast/ep.mp3")]
    response = client.post("/podcasts/fetch", json={"feed_url": "http://f"})
    assert response.status_code == 200
    assert response.json() == {"downloaded": ["ep.mp3"]}
    mock_fetcher.fetch_podcasts.assert_called_once_with("http://f")


def test_podcasts_fetch_missing_url():
    response = client.post("/podcasts/fetch", json={})
    assert response.status_code == 400


@mock.patch.object(app_module, "podcast_fetcher")
def test_podcasts_fetch_error(mock_fetcher):
    mock_fetcher.fetch_podcasts.side_effect = RuntimeError("boom")
    response = client.post("/podcasts/fetch", json={"feed_url": "http://f"})
    assert response.status_code == 500
    assert "boom" in response.text
    mock_fetcher.fetch_podcasts.assert_called_once_with("http://f")


@mock.patch.object(app_module, "get_stats", return_value={"music": 1})
def test_stats_endpoint(mock_stats):
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json() == {"music": 1}
    mock_stats.assert_called_once_with(app_module.config.IPOD_DEVICE)


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>iPod Dock</title>" in response.text


def test_audible_page():
    response = client.get("/audible")
    assert response.status_code == 200
    assert "Audible Library Converter" in response.text


@mock.patch.object(app_module, "playback_controller")
def test_control_endpoint(mock_ctl):
    response = client.post("/control/play")
    assert response.status_code == 200
    mock_ctl.play_pause.assert_called_once()


@mock.patch.object(app_module, "playback_controller")
def test_control_invalid(mock_ctl):
    response = client.post("/control/boom")
    assert response.status_code == 400
    mock_ctl.play_pause.assert_not_called()


@mock.patch.object(app_module.youtube_downloader, "download_audio")
def test_youtube_endpoint(mock_dl):
    mock_dl.return_value = Path("sync_queue/music/song.mp3")
    resp = client.post("/youtube", json={"url": "http://yt"})
    assert resp.status_code == 200
    assert resp.json() == {"queued": "song.mp3", "category": "music"}
    mock_dl.assert_called_once_with("http://yt", "music")


@mock.patch.object(app_module.youtube_downloader, "download_audio")
def test_youtube_category_endpoint(mock_dl):
    mock_dl.return_value = Path("sync_queue/podcast/ep.mp3")
    resp = client.post("/youtube/podcast", json={"url": "http://yt"})
    assert resp.status_code == 200
    assert resp.json() == {"queued": "ep.mp3", "category": "podcast"}
    mock_dl.assert_called_once_with("http://yt", "podcast")


def test_youtube_missing_url():
    resp = client.post("/youtube", json={})
    assert resp.status_code == 400
