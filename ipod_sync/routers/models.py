"""API response models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TrackResponse(BaseModel):
    """Response model for track data."""

    id: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    duration: Optional[int] = Field(None, description="Duration in seconds")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    bitrate: Optional[int] = None
    date_added: Optional[datetime] = None
    play_count: int = 0
    rating: int = Field(0, ge=0, le=5, description="Rating from 0-5 stars")
    category: str = Field("music", description="Track category")
    status: str = Field("active", description="Track status")

    class Config:
        schema_extra = {
            "example": {
                "id": "track123",
                "title": "Example Song",
                "artist": "Example Artist",
                "album": "Example Album",
                "duration": 240,
                "rating": 4,
                "category": "music",
            }
        }

class PlaylistResponse(BaseModel):
    """Response model for playlist data."""

    id: str
    name: str
    track_count: int = Field(description="Number of tracks in playlist")
    total_duration: Optional[int] = Field(
        None, description="Total duration in seconds"
    )
    date_created: Optional[datetime] = None
    is_smart: bool = False

    class Config:
        schema_extra = {
            "example": {
                "id": "playlist123",
                "name": "My Favorites",
                "track_count": 25,
                "total_duration": 5400,
                "is_smart": False,
            }
        }

class StatsResponse(BaseModel):
    """Response model for statistics."""

    total_tracks: int
    total_duration_seconds: int
    total_size_bytes: int
    categories: Dict[str, int]
    total_playlists: Optional[int] = None

class PluginResponse(BaseModel):
    identifier: str
    name: str
    status: str
    available: bool
    authenticated: bool
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    """Success response model."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

# Request models
class CreatePlaylistRequest(BaseModel):
    """Request model for creating playlists."""

    name: str = Field(..., min_length=1, max_length=100)
    track_ids: List[str] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "name": "Road Trip Mix",
                "track_ids": ["track1", "track2", "track3"],
            }
        }

class UpdateTrackRequest(BaseModel):
    """Request model for updating track metadata."""

    title: Optional[str] = Field(None, min_length=1)
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    rating: Optional[int] = Field(None, ge=0, le=5)

class PluginActionRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}

class YouTubeDownloadRequest(BaseModel):
    """Request model for YouTube downloads."""

    url: str = Field(..., pattern=r'https?://(www\.)?(youtube\.com|youtu\.be)/.+')
    category: str = Field("music", pattern=r'^(music|audiobook|podcast)$')

class PodcastFetchRequest(BaseModel):
    """Request model for podcast fetching."""

    feed_url: str = Field(..., pattern=r'https?://.+')
    max_episodes: int = Field(10, ge=1, le=100)
