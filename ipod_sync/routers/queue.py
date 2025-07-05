"""Queue management API router."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from .models import TrackResponse, SuccessResponse
from ..repositories.factory import get_queue_repo
from ..repositories import Repository, Track, QueueRepository
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])

def get_queue_repository() -> Repository:
    """Dependency to get queue repository."""
    return get_queue_repo()

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
async def get_queue(
    repo: Repository = Depends(get_queue_repository),
    _: None = Depends(verify_api_key)
):
    """Get all tracks in the sync queue."""
    try:
        tracks = repo.get_tracks()
        return [track_to_response(track) for track in tracks]
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get queue: {str(e)}")

@router.post("/upload")
async def upload_to_queue(
    file: UploadFile = File(...),
    category: str = "music",
    repo: QueueRepository = Depends(get_queue_repository),
    _: None = Depends(verify_api_key)
):
    """Upload a file to the sync queue."""
    try:
        if category not in {"music", "audiobook", "podcast"}:
            raise HTTPException(400, "Invalid category")
        
        data = await file.read()
        path = repo.save_to_queue(file.filename, data, category=category)
        
        return {"success": True, "queued": path.name, "category": category}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to upload file: {str(e)}")

@router.delete("/{track_id}")
async def remove_from_queue(
    track_id: str,
    repo: Repository = Depends(get_queue_repository),
    _: None = Depends(verify_api_key)
):
    """Remove a track from the sync queue."""
    try:
        success = repo.remove_track(track_id)
        if not success:
            raise HTTPException(404, "Track not found in queue")
        
        return {"success": True, "message": f"Track {track_id} removed from queue"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to remove track from queue: {str(e)}")

@router.post("/clear")
async def clear_queue(
    repo: Repository = Depends(get_queue_repository),
    _: None = Depends(verify_api_key)
):
    """Clear all tracks from the sync queue."""
    try:
        if hasattr(repo, 'clear_queue'):
            success = repo.clear_queue()
        else:
            # Fallback: remove all tracks individually
            tracks = repo.get_tracks()
            success = all(repo.remove_track(track.id) for track in tracks)
        
        if not success:
            raise HTTPException(500, "Failed to clear queue")
        
        return {"success": True, "message": "Queue cleared"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to clear queue: {str(e)}")

@router.get("/stats")
async def get_queue_stats(
    repo: Repository = Depends(get_queue_repository),
    _: None = Depends(verify_api_key)
):
    """Get queue statistics."""
    try:
        stats = repo.get_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get queue stats: {str(e)}")