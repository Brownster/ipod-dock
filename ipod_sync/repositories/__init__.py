"""Repository pattern for data access abstraction."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class TrackStatus(Enum):
    ACTIVE = "active"
    DELETED = "deleted"
    PENDING = "pending"

@dataclass
class Track:
    """Unified track representation across all repositories with gtkpod-inspired extended metadata."""
    id: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    duration: Optional[int] = None  # seconds
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    play_count: int = 0
    rating: int = 0  # 0-5 stars
    status: TrackStatus = TrackStatus.ACTIVE
    category: str = "music"  # music, audiobook, podcast
    metadata: Optional[Dict[str, Any]] = None
    
    # Extended metadata inspired by gtkpod's ExtraTrackData
    pc_path_utf8: Optional[str] = None     # Original PC file path (UTF-8)
    mtime: Optional[datetime] = None       # File modification time
    converted_file: Optional[str] = None   # Path to converted version if exists
    orig_filesize: Optional[int] = None    # Size of original file before conversion
    sha1_hash: Optional[str] = None        # SHA1 hash for integrity checking
    charset: Optional[str] = None          # Character encoding used for ID3 tags
    lyrics: Optional[str] = None           # Full lyrics text
    
    # Additional comprehensive metadata
    year: Optional[int] = None             # Release year
    track_total: Optional[int] = None      # Total tracks on album
    disc_number: Optional[int] = None      # Disc number
    disc_total: Optional[int] = None       # Total discs
    composer: Optional[str] = None         # Composer name
    albumartist: Optional[str] = None      # Album artist
    bpm: Optional[int] = None              # Beats per minute
    compilation: Optional[bool] = None     # Is compilation album
    
    # Sort fields for proper ordering
    sort_artist: Optional[str] = None      # Artist sort name
    sort_title: Optional[str] = None       # Title sort name
    sort_album: Optional[str] = None       # Album sort name
    sort_albumartist: Optional[str] = None # Album artist sort name
    
    # Podcast/audiobook specific fields
    description: Optional[str] = None      # Episode/chapter description
    podcasturl: Optional[str] = None       # Podcast URL
    podcastrss: Optional[str] = None       # Podcast RSS feed
    subtitle: Optional[str] = None         # Episode subtitle
    
    # Sync tracking
    sync_status: str = "pending"           # pending, synced, error
    last_synced: Optional[datetime] = None # Last sync timestamp
    sync_error: Optional[str] = None       # Last sync error message

@dataclass 
class Playlist:
    """Playlist representation."""
    id: str
    name: str
    track_ids: List[str]
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    is_smart: bool = False
    smart_criteria: Optional[Dict[str, Any]] = None

class Repository(ABC):
    """Base repository interface for data access."""
    
    @abstractmethod
    def get_tracks(self, limit: Optional[int] = None, offset: int = 0) -> List[Track]:
        """Get all tracks with optional pagination."""
        pass
    
    @abstractmethod
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get a specific track by ID."""
        pass
    
    @abstractmethod
    def add_track(self, track: Track) -> str:
        """Add a track and return its ID."""
        pass
    
    @abstractmethod
    def update_track(self, track: Track) -> bool:
        """Update an existing track."""
        pass
    
    @abstractmethod
    def remove_track(self, track_id: str) -> bool:
        """Remove a track by ID."""
        pass
    
    @abstractmethod
    def search_tracks(self, query: str, fields: List[str] = None) -> List[Track]:
        """Search tracks by query in specified fields."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        pass

class PlaylistRepository(ABC):
    """Base playlist repository interface."""
    
    @abstractmethod
    def get_playlists(self) -> List[Playlist]:
        """Get all playlists."""
        pass
    
    @abstractmethod
    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Get a specific playlist by ID."""
        pass
    
    @abstractmethod
    def create_playlist(self, name: str, track_ids: List[str] = None) -> str:
        """Create a new playlist and return its ID."""
        pass
    
    @abstractmethod
    def update_playlist(self, playlist: Playlist) -> bool:
        """Update an existing playlist."""
        pass
    
    @abstractmethod
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist by ID."""
        pass
    
    @abstractmethod
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Add tracks to a playlist."""
        pass
    
    @abstractmethod
    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Remove tracks from a playlist."""
        pass

# Import concrete implementations
from .queue_repository import QueueRepository
from .ipod_repository import IpodRepository
from .local_repository import LocalRepository

__all__ = [
    'Track',
    'Playlist', 
    'TrackStatus',
    'Repository',
    'PlaylistRepository',
    'QueueRepository',
    'IpodRepository',
    'LocalRepository',
]