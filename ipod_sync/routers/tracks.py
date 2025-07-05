"""Tracks API router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse

from .models import (
    TrackResponse,
    StatsResponse,
    ErrorResponse,
    UpdateTrackRequest,
    SuccessResponse,
)
from ..repositories.factory import get_ipod_repo, get_queue_repo
from ..repositories import Repository, Track
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/tracks", tags=["tracks"])

def get_track_repository(source: str = Query("ipod", enum=["ipod", "queue"])) -> Repository:
    """Dependency to get track repository."""
    if source == "ipod":
        return get_ipod_repo()
    elif source == "queue":
        return get_queue_repo()
    else:
        raise HTTPException(400, f"Invalid source: {source}")

def track_to_response(track: Track) -> TrackResponse:
    """Convert Track to TrackResponse."""
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

@router.get("/", response_model=List[TrackResponse])
async def get_tracks(
    source: str = Query("ipod", enum=["ipod", "queue"]),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
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

@router.get(
    "/{track_id}",
    response_model=TrackResponse,
    summary="Get track by ID",
    responses={404: {"model": ErrorResponse}},
)
async def get_track(
    track_id: str = Path(..., description="Track identifier"),
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Get a specific track."""
    try:
        track = repo.get_track(track_id)
        if not track:
            raise HTTPException(404, "Track not found")
        
        return track_to_response(track)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get track: {str(e)}")

@router.put(
    "/{track_id}",
    response_model=SuccessResponse,
    summary="Update track metadata",
)
async def update_track(
    request: UpdateTrackRequest,
    track_id: str = Path(..., description="Track identifier"),
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key),
):
    """Update track metadata."""
    try:
        track = repo.get_track(track_id)
        if not track:
            raise HTTPException(404, "Track not found")

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

        success = repo.update_track(track)
        if not success:
            raise HTTPException(500, "Failed to update track")

        return SuccessResponse(message=f"Track '{track.title}' updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update track: {str(e)}")

@router.delete("/{track_id}")
async def delete_track(
    track_id: str,
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Delete a track."""
    try:
        success = repo.remove_track(track_id)
        if not success:
            raise HTTPException(404, "Track not found")
        
        return {"success": True, "message": f"Track {track_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete track: {str(e)}")

@router.get(
    "/stats/summary",
    response_model=StatsResponse,
    summary="Get track statistics",
)
async def get_track_stats(
    source: str = Query("ipod", enum=["ipod", "queue"]),
    repo: Repository = Depends(get_track_repository),
    _: None = Depends(verify_api_key)
):
    """Get track statistics."""
    try:
        stats = repo.get_stats()
        return StatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get stats: {str(e)}")