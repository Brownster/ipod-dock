"""Playlists API router."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from .models import PlaylistResponse, CreatePlaylistRequest, SuccessResponse
from ..repositories.factory import get_ipod_repo
from ..repositories import PlaylistRepository, Playlist
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/playlists", tags=["playlists"])

def get_playlist_repository() -> PlaylistRepository:
    """Dependency to get playlist repository."""
    return get_ipod_repo()

def playlist_to_response(playlist: Playlist) -> PlaylistResponse:
    """Convert Playlist to PlaylistResponse."""
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        track_count=len(playlist.track_ids),
        date_created=playlist.date_created,
        is_smart=playlist.is_smart
    )

@router.get("/", response_model=List[PlaylistResponse])
async def get_playlists(
    repo: PlaylistRepository = Depends(get_playlist_repository),
    _: None = Depends(verify_api_key)
):
    """Get all playlists."""
    try:
        playlists = repo.get_playlists()
        return [playlist_to_response(playlist) for playlist in playlists]
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get playlists: {str(e)}")

@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: str,
    repo: PlaylistRepository = Depends(get_playlist_repository),
    _: None = Depends(verify_api_key)
):
    """Get a specific playlist."""
    try:
        playlist = repo.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(404, "Playlist not found")
        
        return playlist_to_response(playlist)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get playlist: {str(e)}")

@router.post("/", response_model=SuccessResponse)
async def create_playlist(
    request: CreatePlaylistRequest,
    repo: PlaylistRepository = Depends(get_playlist_repository),
    _: None = Depends(verify_api_key)
):
    """Create a new playlist."""
    try:
        playlist_id = repo.create_playlist(request.name, request.track_ids)
        return SuccessResponse(
            success=True,
            message=f"Playlist '{request.name}' created",
            data={"playlist_id": playlist_id}
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to create playlist: {str(e)}")

@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: str,
    repo: PlaylistRepository = Depends(get_playlist_repository),
    _: None = Depends(verify_api_key)
):
    """Delete a playlist."""
    try:
        success = repo.delete_playlist(playlist_id)
        if not success:
            raise HTTPException(404, "Playlist not found")
        
        return {"success": True, "message": f"Playlist {playlist_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete playlist: {str(e)}")

@router.post("/{playlist_id}/tracks")
async def add_tracks_to_playlist(
    playlist_id: str,
    track_ids: List[str],
    repo: PlaylistRepository = Depends(get_playlist_repository),
    _: None = Depends(verify_api_key)
):
    """Add tracks to a playlist."""
    try:
        success = repo.add_tracks_to_playlist(playlist_id, track_ids)
        if not success:
            raise HTTPException(404, "Playlist not found")
        
        return {"success": True, "message": f"Added {len(track_ids)} tracks to playlist"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to add tracks to playlist: {str(e)}")

@router.delete("/{playlist_id}/tracks")
async def remove_tracks_from_playlist(
    playlist_id: str,
    track_ids: List[str],
    repo: PlaylistRepository = Depends(get_playlist_repository),
    _: None = Depends(verify_api_key)
):
    """Remove tracks from a playlist."""
    try:
        success = repo.remove_tracks_from_playlist(playlist_id, track_ids)
        if not success:
            raise HTTPException(404, "Playlist not found")
        
        return {"success": True, "message": f"Removed {len(track_ids)} tracks from playlist"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to remove tracks from playlist: {str(e)}")