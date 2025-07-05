"""Tests for repository pattern implementation."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import json

from ipod_sync.repositories import Track, Playlist, TrackStatus, Repository, PlaylistRepository
from ipod_sync.repositories.queue_repository import QueueRepository
from ipod_sync.repositories.factory import RepositoryFactory, get_ipod_repo, get_queue_repo

class TestTrack:
    def test_track_creation(self):
        track = Track(
            id="test123",
            title="Test Track",
            artist="Test Artist",
            album="Test Album"
        )
        
        assert track.id == "test123"
        assert track.title == "Test Track"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.status == TrackStatus.ACTIVE
        assert track.category == "music"
        assert track.play_count == 0
        assert track.rating == 0

class TestPlaylist:
    def test_playlist_creation(self):
        playlist = Playlist(
            id="playlist123",
            name="Test Playlist",
            track_ids=["track1", "track2", "track3"]
        )
        
        assert playlist.id == "playlist123"
        assert playlist.name == "Test Playlist"
        assert len(playlist.track_ids) == 3
        assert "track1" in playlist.track_ids
        assert playlist.is_smart is False

class TestQueueRepository:
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = QueueRepository(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_repository_initialization(self):
        """Test repository creates necessary directories."""
        assert self.temp_dir.exists()
        assert (self.temp_dir / ".queue_metadata.json").exists()
    
    def test_metadata_operations(self):
        """Test metadata loading and saving."""
        test_metadata = {"test_file.mp3": {"title": "Test", "artist": "Artist"}}
        self.repo._save_metadata(test_metadata)
        
        loaded_metadata = self.repo._load_metadata()
        assert loaded_metadata == test_metadata
    
    def test_add_track(self):
        """Test adding a track to queue."""
        track = Track(
            id="test_track",
            title="Test Track",
            artist="Test Artist",
            category="music"
        )
        
        # Create a test audio file
        test_file = self.temp_dir / "test.mp3"
        test_file.write_text("fake mp3 content")
        track.file_path = str(test_file)
        
        track_id = self.repo.add_track(track)
        
        assert track_id is not None
        # Check that file was copied to music subdirectory
        music_dir = self.temp_dir / "music"
        assert music_dir.exists()
        assert any(f.name == "test.mp3" for f in music_dir.iterdir())
    
    def test_get_tracks_empty(self):
        """Test getting tracks from empty repository."""
        tracks = self.repo.get_tracks()
        assert len(tracks) == 0
    
    def test_get_tracks_with_files(self):
        """Test getting tracks with audio files present."""
        # Create test audio files
        music_dir = self.temp_dir / "music"
        music_dir.mkdir()
        
        test_file1 = music_dir / "track1.mp3"
        test_file2 = music_dir / "track2.m4a"
        test_file1.write_text("fake mp3")
        test_file2.write_text("fake m4a")
        
        tracks = self.repo.get_tracks()
        assert len(tracks) == 2
        
        # Check that tracks have correct properties
        track_files = [track.file_path for track in tracks]
        assert str(test_file1) in track_files
        assert str(test_file2) in track_files
    
    def test_remove_track(self):
        """Test removing a track from queue."""
        # Add a track first
        track = Track(id="test", title="Test", category="music")
        test_file = self.temp_dir / "test.mp3"
        test_file.write_text("fake mp3")
        track.file_path = str(test_file)
        
        track_id = self.repo.add_track(track)
        
        # Verify track exists
        tracks_before = self.repo.get_tracks()
        assert len(tracks_before) == 1
        
        # Remove track
        success = self.repo.remove_track(track_id)
        assert success is True
        
        # Verify track is gone
        tracks_after = self.repo.get_tracks()
        assert len(tracks_after) == 0
    
    def test_search_tracks(self):
        """Test searching tracks by query."""
        # Create tracks with metadata
        metadata = self.repo._load_metadata()
        metadata["music/rock_song.mp3"] = {
            "title": "Rock Song",
            "artist": "Rock Artist",
            "genre": "Rock"
        }
        metadata["music/pop_song.mp3"] = {
            "title": "Pop Song", 
            "artist": "Pop Artist",
            "genre": "Pop"
        }
        self.repo._save_metadata(metadata)
        
        # Create actual files
        music_dir = self.temp_dir / "music"
        music_dir.mkdir()
        (music_dir / "rock_song.mp3").write_text("fake")
        (music_dir / "pop_song.mp3").write_text("fake")
        
        # Search by artist
        rock_tracks = self.repo.search_tracks("Rock")
        assert len(rock_tracks) == 1
        assert "Rock" in rock_tracks[0].artist
        
        # Search by title
        pop_tracks = self.repo.search_tracks("Pop Song")
        assert len(pop_tracks) == 1
        assert pop_tracks[0].title == "Pop Song"
    
    def test_get_stats(self):
        """Test getting repository statistics."""
        # Create test tracks with different categories
        music_dir = self.temp_dir / "music"
        audiobook_dir = self.temp_dir / "audiobook"
        music_dir.mkdir()
        audiobook_dir.mkdir()
        
        (music_dir / "song.mp3").write_text("fake music")
        (audiobook_dir / "book.m4b").write_text("fake audiobook")
        
        # Add metadata
        metadata = {
            "music/song.mp3": {"category": "music", "duration": 180},
            "audiobook/book.m4b": {"category": "audiobook", "duration": 3600}
        }
        self.repo._save_metadata(metadata)
        
        stats = self.repo.get_stats()
        
        assert stats["total_tracks"] == 2
        assert stats["total_duration_seconds"] == 3780  # 180 + 3600
        assert stats["categories"]["music"] == 1
        assert stats["categories"]["audiobook"] == 1
    
    def test_clear_queue(self):
        """Test clearing all tracks from queue."""
        # Add some test files
        music_dir = self.temp_dir / "music"
        music_dir.mkdir()
        (music_dir / "track1.mp3").write_text("fake")
        (music_dir / "track2.mp3").write_text("fake")
        
        # Verify files exist
        tracks_before = self.repo.get_tracks()
        assert len(tracks_before) == 2
        
        # Clear queue
        success = self.repo.clear_queue()
        assert success is True
        
        # Verify queue is empty
        tracks_after = self.repo.get_tracks()
        assert len(tracks_after) == 0
        
        # Verify metadata is cleared
        metadata = self.repo._load_metadata()
        assert len(metadata) == 0

class TestRepositoryFactory:
    @patch('ipod_sync.repositories.factory.config')
    def test_create_queue_repository(self, mock_config):
        """Test creating queue repository."""
        mock_config.SYNC_QUEUE_DIR = Path("/tmp/test_queue")
        
        repo = RepositoryFactory.create_queue_repository()
        assert isinstance(repo, QueueRepository)
    
    @patch('ipod_sync.repositories.factory.config')
    def test_get_repository(self, mock_config):
        """Test getting repository by type."""
        mock_config.SYNC_QUEUE_DIR = Path("/tmp/test_queue")
        
        repo = RepositoryFactory.get_repository("queue")
        assert isinstance(repo, QueueRepository)
        
        with pytest.raises(ValueError):
            RepositoryFactory.get_repository("invalid_type")
    
    @patch('ipod_sync.repositories.factory.config')
    def test_convenience_functions(self, mock_config):
        """Test convenience functions."""
        mock_config.SYNC_QUEUE_DIR = Path("/tmp/test_queue")
        mock_config.IPOD_DEVICE = "/dev/test"
        
        queue_repo = get_queue_repo()
        assert isinstance(queue_repo, QueueRepository)

class TestTrackStatus:
    def test_track_status_enum(self):
        """Test TrackStatus enum values."""
        assert TrackStatus.ACTIVE.value == "active"
        assert TrackStatus.DELETED.value == "deleted"
        assert TrackStatus.PENDING.value == "pending"