"""API response models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class TrackResponse(BaseModel):
    id: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    bitrate: Optional[int] = None
    date_added: Optional[datetime] = None
    play_count: int = 0
    rating: int = 0
    category: str = "music"
    status: str = "active"

class PlaylistResponse(BaseModel):
    id: str
    name: str
    track_count: int
    total_duration: Optional[int] = None
    date_created: Optional[datetime] = None
    is_smart: bool = False

class StatsResponse(BaseModel):
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
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Request models
class CreatePlaylistRequest(BaseModel):
    name: str
    track_ids: List[str] = []

class PluginActionRequest(BaseModel):
    action: str
    parameters: Dict[str, Any] = {}

class YouTubeDownloadRequest(BaseModel):
    url: str
    category: str = "music"

class PodcastFetchRequest(BaseModel):
    feed_url: str
    max_episodes: int = 10