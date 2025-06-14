from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from ipod_sync.app import app
import ipod_sync.app as app_module

client = TestClient(app)


def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_upload_category_invalid():
    response = client.post("/upload/invalid", files={"file": ("foo.mp3", b"abc")})
    assert response.status_code == 400


@mock.patch.object(app_module, "get_tracks", return_value=[{"id": "1"}])
def test_tracks_endpoint(mock_get):
    response = client.get("/tracks")
    assert response.status_code == 200
    assert response.json() == [{"id": "1"}]
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

def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>iPod Dock</title>" in response.text
