from pathlib import Path
from unittest import mock
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from ipod_sync.app import app
import ipod_sync.audible_import as audible_import

client = TestClient(app)

pytest.skip("Audible endpoints deprecated in API v2", allow_module_level=True)


@mock.patch.object(audible_import, "fetch_library")
def test_library_endpoint(mock_fetch):
    mock_fetch.return_value = [{"asin": "A1", "title": "Book"}]
    audible_import.IS_AUTHENTICATED = True
    resp = client.get("/api/library")
    assert resp.status_code == 200
    assert resp.json() == [{"asin": "A1", "title": "Book"}]
    mock_fetch.assert_called_once()


@mock.patch.object(audible_import, "queue_conversion")
def test_convert_endpoint(mock_queue):
    audible_import.IS_AUTHENTICATED = True
    resp = client.post("/api/convert", json={"asin": "A1", "title": "Book"})
    assert resp.status_code == 200
    assert resp.json()["message"]
    mock_queue.assert_called_once_with("A1", "Book")


def test_status_endpoint():
    audible_import.JOBS.clear()
    audible_import.JOBS["A1"] = {"status": "queued"}
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert resp.json() == {"A1": {"status": "queued"}}


def test_download_endpoint(tmp_path):
    file_path = tmp_path / "out.m4b"
    file_path.write_text("data")
    audible_import.DOWNLOADS_DIR = tmp_path
    resp = client.get(f"/downloads/{file_path.name}")
    assert resp.status_code == 200
    assert resp.content == b"data"


@mock.patch.object(audible_import, "check_authentication")
def test_auth_status_endpoint(mock_check):
    mock_check.return_value = True
    audible_import.IS_AUTHENTICATED = True
    resp = client.get("/api/auth/status")
    assert resp.status_code == 200
    assert resp.json() == {"authenticated": True}


def test_library_requires_auth():
    audible_import.IS_AUTHENTICATED = False
    resp = client.get("/api/library")
    assert resp.status_code == 401


def test_convert_requires_auth():
    audible_import.IS_AUTHENTICATED = False
    resp = client.post("/api/convert", json={"asin": "A", "title": "B"})
    assert resp.status_code == 401
