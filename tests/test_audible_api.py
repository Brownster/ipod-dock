from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from ipod_sync.app import app
import ipod_sync.app as app_module

client = TestClient(app)


@mock.patch.object(app_module.audible_import, "fetch_library")
def test_library_endpoint(mock_fetch):
    mock_fetch.return_value = [{"asin": "A1", "title": "Book"}]
    resp = client.get("/api/library")
    assert resp.status_code == 200
    assert resp.json() == [{"asin": "A1", "title": "Book"}]
    mock_fetch.assert_called_once()


@mock.patch.object(app_module.audible_import, "queue_conversion")
def test_convert_endpoint(mock_queue):
    resp = client.post("/api/convert", json={"asin": "A1", "title": "Book"})
    assert resp.status_code == 200
    assert resp.json()["message"]
    mock_queue.assert_called_once_with("A1", "Book")


def test_status_endpoint():
    app_module.audible_import.JOBS.clear()
    app_module.audible_import.JOBS["A1"] = {"status": "queued"}
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert resp.json() == {"A1": {"status": "queued"}}


def test_download_endpoint(tmp_path):
    file_path = tmp_path / "out.m4b"
    file_path.write_text("data")
    app_module.audible_import.DOWNLOADS_DIR = tmp_path
    resp = client.get(f"/downloads/{file_path.name}")
    assert resp.status_code == 200
    assert resp.content == b"data"
