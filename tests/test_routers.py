"""Tests for API routers."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync.app import app
from ipod_sync.repositories import Track, TrackStatus

client = TestClient(app)

class TestTracksRouter:
    @patch('ipod_sync.routers.tracks.get_ipod_repo')
    def test_get_tracks(self, mock_repo):
        """Test GET /api/v1/tracks endpoint."""
        mock_track = Track(
            id="test123",
            title="Test Track",
            artist="Test Artist",
            status=TrackStatus.ACTIVE,
        )
        mock_repo.return_value.get_tracks.return_value = [mock_track]

        with patch('ipod_sync.auth.verify_api_key', return_value=None):
            response = client.get("/api/v1/tracks?source=ipod")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Track"

    @patch('ipod_sync.routers.tracks.get_ipod_repo')
    def test_get_track_not_found(self, mock_repo):
        """Test GET /api/v1/tracks/{id} with non-existent track."""
        mock_repo.return_value.get_track.return_value = None

        with patch('ipod_sync.auth.verify_api_key', return_value=None):
            response = client.get("/api/v1/tracks/nonexistent")

        assert response.status_code == 404

    def test_authentication_required(self):
        """Test that endpoints require authentication."""
        response = client.get("/api/v1/tracks")
        assert response.status_code == 401

