# Task 3: Refactor FastAPI Application Structure

**Priority**: Medium  
**Estimated Time**: 2-3 days  
**Skills Required**: FastAPI, Python modules, API design  
**Assigned to**: _[Developer Name]_  
**Depends on**: Task 2 (Repository Pattern) should be completed first

## Overview
Split the monolithic `app.py` into focused router modules and update the application to use the new repository pattern. This will improve code organization, make endpoints easier to maintain, and provide better API structure.

## Learning Objectives
- Understand FastAPI router organization
- Learn dependency injection patterns
- Practice API versioning strategies
- Implement proper error handling
- Design RESTful API structures

## Acceptance Criteria
- [ ] Application split into focused routers (tracks, playlists, queue, plugins)
- [ ] All endpoints updated to use repository pattern
- [ ] Dependency injection for repositories
- [ ] API versioning implemented (`/api/v1/...`)
- [ ] Improved error handling and response models
- [ ] Backward compatibility maintained during transition
- [ ] API documentation updated

## Background Context
The current `app.py` file mixes multiple concerns (tracks, playlists, uploads, plugins) in a single file. GTKPod's modular architecture inspired this refactoring to organize endpoints by domain and use dependency injection for better testability.

## Implementation Steps

### Step 3.1: Create API Models (0.5 days)

**File**: `ipod_sync/routers/models.py`

```python
"""API response and request models."""
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
    bitrate: Optional[int] = Field(None, description="Bitrate in kbps")
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
                "category": "music"
            }
        }

class PlaylistResponse(BaseModel):
    """Response model for playlist data."""
    id: str
    name: str
    track_count: int = Field(description="Number of tracks in playlist")
    total_duration: Optional[int] = Field(None, description="Total duration in seconds")
    date_created: Optional[datetime] = None
    is_smart: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "id": "playlist123",
                "name": "My Favorites",
                "track_count": 25,
                "total_duration": 5400,
                "is_smart": False
            }
        }

class StatsResponse(BaseModel):
    """Response model for statistics."""
    total_tracks: int
    total_duration_seconds: int
    total_size_bytes: int
    categories: Dict[str, int]
    total_playlists: Optional[int] = None

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
                "track_ids": ["track1", "track2", "track3"]
            }
        }

class UpdateTrackRequest(BaseModel):
    """Request model for updating track metadata."""
    title: Optional[str] = Field(None, min_length=1)
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    rating: Optional[int] = Field(None, ge=0, le=5)

class YouTubeDownloadRequest(BaseModel):
    """Request model for YouTube downloads."""
    url: str = Field(..., regex=r'https?://(www\.)?(youtube\.com|youtu\.be)/.+')
    category: str = Field("music", regex=r'^(music|audiobook|podcast)$')
    
class PodcastFetchRequest(BaseModel):
    """Request model for podcast fetching."""
    feed_url: str = Field(..., regex=r'https?://.+')
    max_episodes: int = Field(10, ge=1, le=100)
```

**What to implement:**
1. **Study current API responses**: Look at what `app.py` currently returns
2. **Create comprehensive models**: Cover all current and planned endpoints
3. **Add validation**: Use Pydantic field validators for data integrity
4. **Include examples**: Add schema examples for better API documentation
5. **Error handling models**: Standardize error response format

**Key concepts:**
- **Pydantic models**: Automatic validation and serialization
- **Field constraints**: Validation rules for inputs
- **Schema examples**: Improve API documentation
- **Response standardization**: Consistent API responses

### Step 3.2: Create Tracks Router (1 day)

**File**: `ipod_sync/routers/tracks.py`

```python
"""Tracks API router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse

from .models import TrackResponse, StatsResponse, UpdateTrackRequest, SuccessResponse
from ..repositories.factory import get_ipod_repo, get_queue_repo
from ..repositories import Repository, Track
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/tracks", tags=["tracks"])

def get_track_repository(source: str = Query("ipod", enum=["ipod", "queue"])) -> Repository:
    """Dependency to get track repository based on source."""
    if source == "ipod":
        return get_ipod_repo()
    elif source == "queue":
        return get_queue_repo()
    else:
        raise HTTPException(400, f"Invalid source: {source}")

def track_to_response(track: Track) -> TrackResponse:
    """Convert Track domain object to API response model."""
    return TrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        genre=track.genre,
        track_number=track.track_number,
        duration=track.duration,
        file_size=track.file_size,
        bitrate=track.bitrate,
        date_added=track.date_added,
        play_count=track.play_count,
        rating=track.rating,
        category=track.category,
        status=track.status.value
    )

@router.get("/", 
    response_model=List[TrackResponse],
    summary="Get tracks",
    description="Retrieve tracks from specified source with optional filtering and pagination"
)
async def get_tracks(
    source: str = Query("ipod", enum=["ipod", "queue"], description="Data source"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum tracks to return"),
    offset: int = Query(0, ge=0, description="Number of tracks to skip"),
    search: Optional[str] = Query(None, description="Search query for track metadata"),
    category: Optional[str] = Query(None, enum=["music", "audiobook", "podcast"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Get tracks from specified source."""
    try:
        if search:
            tracks = repo.search_tracks(search)
        else:
            tracks = repo.get_tracks(limit=limit, offset=offset)
        
        # Filter by category if specified
        if category:
            tracks = [t for t in tracks if t.category == category]
        
        return [track_to_response(track) for track in tracks]
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get tracks: {str(e)}")

@router.get("/{track_id}", 
    response_model=TrackResponse,
    summary="Get track by ID",
    responses={404: {"model": ErrorResponse}}
)
async def get_track(
    track_id: str = Path(..., description="Track identifier"),
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Get a specific track by ID."""
    try:
        track = repo.get_track(track_id)
        if not track:
            raise HTTPException(404, "Track not found")
        
        return track_to_response(track)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get track: {str(e)}")

@router.put("/{track_id}",
    response_model=SuccessResponse,
    summary="Update track metadata"
)
async def update_track(
    track_id: str = Path(..., description="Track identifier"),
    request: UpdateTrackRequest,
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Update track metadata."""
    try:
        # Get existing track
        track = repo.get_track(track_id)
        if not track:
            raise HTTPException(404, "Track not found")
        
        # Update fields that were provided
        if request.title is not None:
            track.title = request.title
        if request.artist is not None:
            track.artist = request.artist
        if request.album is not None:
            track.album = request.album
        if request.genre is not None:
            track.genre = request.genre
        if request.rating is not None:
            track.rating = request.rating
        
        # Save changes
        success = repo.update_track(track)
        if not success:
            raise HTTPException(500, "Failed to update track")
        
        return SuccessResponse(
            message=f"Track '{track.title}' updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update track: {str(e)}")

@router.delete("/{track_id}",
    response_model=SuccessResponse,
    summary="Delete track"
)
async def delete_track(
    track_id: str = Path(..., description="Track identifier"),
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Delete a track from the specified source."""
    try:
        success = repo.remove_track(track_id)
        if not success:
            raise HTTPException(404, "Track not found")
        
        return SuccessResponse(
            message=f"Track {track_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete track: {str(e)}")

@router.get("/stats/summary", 
    response_model=StatsResponse,
    summary="Get track statistics"
)
async def get_track_stats(
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Get statistical information about tracks."""
    try:
        stats = repo.get_stats()
        return StatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get stats: {str(e)}")
```

**What to implement:**
1. **Study existing endpoints**: Look at current track operations in `app.py`
2. **Implement CRUD operations**: Create, Read, Update, Delete for tracks
3. **Add proper validation**: Use Pydantic models for request validation
4. **Dependency injection**: Use FastAPI dependencies for repositories
5. **Error handling**: Comprehensive error responses with proper HTTP codes
6. **Documentation**: Add OpenAPI descriptions and examples

**Key concepts:**
- **FastAPI routers**: Modular endpoint organization
- **Dependency injection**: Clean way to provide services
- **Path/Query parameters**: Different ways to pass data
- **Response models**: Type-safe API responses

### Step 3.3: Create Additional Routers (1 day)

Create similar routers for other domains:

**`ipod_sync/routers/playlists.py`** - Playlist management
**`ipod_sync/routers/queue.py`** - Sync queue operations  
**`ipod_sync/routers/plugins.py`** - Plugin management
**`ipod_sync/routers/control.py`** - System control (sync, playback)
**`ipod_sync/routers/config.py`** - Configuration management

Each router should follow the same patterns:
- Use dependency injection for repositories
- Proper error handling with HTTP status codes
- Comprehensive request/response models
- API documentation with examples
- Authentication via `verify_api_key`

**Example playlist router structure:**
```python
"""Playlists API router."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from .models import PlaylistResponse, CreatePlaylistRequest, SuccessResponse
from ..repositories.factory import get_ipod_repo
from ..repositories import PlaylistRepository

router = APIRouter(prefix="/api/v1/playlists", tags=["playlists"])

@router.get("/", response_model=List[PlaylistResponse])
async def get_playlists(
    repo: PlaylistRepository = Depends(get_ipod_repo),
    _: None = Depends(verify_api_key)
):
    """Get all playlists."""
    # Implementation...

@router.post("/", response_model=SuccessResponse)
async def create_playlist(
    request: CreatePlaylistRequest,
    repo: PlaylistRepository = Depends(get_ipod_repo),
    _: None = Depends(verify_api_key)
):
    """Create a new playlist."""
    # Implementation...
```

### Step 3.4: Update Main Application (0.5 days)

**File**: `ipod_sync/app.py`

```python
"""FastAPI application with modular router structure."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from importlib import resources

from .routers import tracks, playlists, queue, plugins, control, config as config_router
from .plugins.manager import plugin_manager
from .logging_setup import setup_logging
from . import config

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting ipod-dock API v2.0")
    
    # Initialize plugin system
    plugin_manager.discover_plugins()
    logger.info(f"Discovered {len(plugin_manager._plugin_classes)} plugins")
    
    # Validate configuration
    try:
        from .config.manager import config_manager
        config_manager._validate_configuration()
        logger.info("Configuration validation passed")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ipod-dock API")

app = FastAPI(
    title="iPod Dock API",
    description="Advanced iPod management and media syncing API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.config_manager.config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = resources.files("ipod_sync").joinpath("static")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include all routers
app.include_router(tracks.router)
app.include_router(playlists.router)
app.include_router(queue.router)
app.include_router(plugins.router)
app.include_router(control.router)
app.include_router(config_router.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception in {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url.path)
        }
    )

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve the main dashboard."""
    page = resources.files("ipod_sync.templates").joinpath("index.html")
    return page.read_text(encoding="utf-8")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

# Legacy endpoints for backward compatibility
@app.get("/status")
async def legacy_status():
    """Legacy status endpoint - redirects to new API."""
    from .api_helpers import is_ipod_connected
    connected = is_ipod_connected(config.IPOD_DEVICE)
    return {
        "status": "ok", 
        "connected": connected,
        "message": "This endpoint is deprecated. Use /api/v1/control/status instead."
    }

def main() -> None:
    """Run development server."""
    import uvicorn
    
    setup_logging()
    logger.info("Starting development server")
    
    uvicorn.run(
        "ipod_sync.app:app",
        host=config.config_manager.config.server.host,
        port=config.config_manager.config.server.port,
        log_level="info",
        reload=True
    )

if __name__ == "__main__":
    main()
```

**What to implement:**
1. **Router integration**: Include all domain-specific routers
2. **Lifecycle management**: Proper startup/shutdown handling
3. **Error handling**: Global exception handler for debugging
4. **Backward compatibility**: Keep legacy endpoints working
5. **Configuration integration**: Use new config system
6. **Documentation**: Ensure OpenAPI docs are comprehensive

## Migration Strategy

### Phase 1: Parallel Implementation
1. Create new routers alongside existing `app.py`
2. Test new endpoints thoroughly
3. Ensure feature parity with existing API

### Phase 2: Gradual Migration
1. Update frontend to use new endpoints
2. Add deprecation warnings to old endpoints
3. Monitor usage of legacy endpoints

### Phase 3: Cleanup
1. Remove unused code from original `app.py`
2. Update all documentation
3. Remove legacy endpoints

## Testing Requirements

**File**: `tests/test_routers.py`

```python
"""Tests for API routers."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from ipod_sync.app import app
from ipod_sync.repositories import Track, TrackStatus

client = TestClient(app)

class TestTracksRouter:
    @patch('ipod_sync.routers.tracks.get_ipod_repo')
    def test_get_tracks(self, mock_repo):
        """Test GET /api/v1/tracks endpoint."""
        # Mock repository
        mock_track = Track(
            id="test123",
            title="Test Track",
            artist="Test Artist",
            status=TrackStatus.ACTIVE
        )
        mock_repo.return_value.get_tracks.return_value = [mock_track]
        
        # Mock authentication
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
        assert response.status_code == 401  # or whatever your auth returns
```

**Test coverage requirements:**
- [ ] All router endpoints (GET, POST, PUT, DELETE)
- [ ] Request validation (invalid inputs)
- [ ] Response serialization
- [ ] Error handling scenarios
- [ ] Authentication requirements
- [ ] Repository integration

## Troubleshooting Guide

### Common Issues

**Import errors with routers:**
- Check that all router files have proper imports
- Verify dependency injection is working
- Ensure repositories are available

**Authentication not working:**
- Check that `verify_api_key` is properly imported
- Verify API key configuration
- Test authentication separately

**Repository dependency injection fails:**
- Ensure repository factory is working
- Check configuration is loaded properly
- Verify FastAPI dependency system

### Testing Tips

**Mock repositories for testing:**
```python
@patch('module.get_repo')
def test_endpoint(self, mock_repo):
    mock_repo.return_value.method.return_value = expected_result
    # Test endpoint
```

**Test with TestClient:**
```python
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get("/api/v1/tracks")
```

## Success Criteria

When this task is complete, you should have:

1. **Modular API structure** with domain-specific routers
2. **Repository integration** throughout all endpoints
3. **Comprehensive validation** using Pydantic models
4. **Proper error handling** with meaningful HTTP status codes
5. **API versioning** for future compatibility
6. **Backward compatibility** for existing clients
7. **Comprehensive tests** for all endpoints

## Next Steps

After completing this task:
- Frontend can be updated to use new API structure
- API documentation will be automatically generated
- New features can be added to appropriate routers
- Monitoring and analytics can be added per domain

## Resources

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Pydantic models guide](https://pydantic-docs.helpmanual.io/)
- [API design best practices](https://swagger.io/resources/articles/best-practices-in-api-design/)
- Existing `app.py` for current endpoint reference

## Questions for Code Review

1. Are all endpoints properly organized by domain?
2. Do the Pydantic models cover all necessary validation?
3. Is error handling consistent across all routers?
4. Are the repository dependencies injected correctly?
5. Is the API versioning strategy appropriate?
6. Does the migration maintain backward compatibility?