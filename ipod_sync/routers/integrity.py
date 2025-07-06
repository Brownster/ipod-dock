"""Integrity checking and smart playlist API router."""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel

from .models import TrackResponse, SuccessResponse
from ..repositories.factory import get_queue_repo, get_ipod_repo
from ..repositories import Repository, Track
from ..integrity import file_integrity_manager, duplicate_resolver
from ..smart_playlists import create_smart_playlist_generator, create_playlist_analyzer
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/integrity", tags=["integrity"])


class DuplicateGroup(BaseModel):
    """Duplicate file group representation."""
    hash: str
    files: List[str]
    total_size: int
    suggested_action: str


class IntegrityReport(BaseModel):
    """File integrity check report."""
    total_files_checked: int
    files_with_issues: int
    duplicate_groups: List[DuplicateGroup]
    corrupted_files: List[str]
    missing_files: List[str]


class SmartPlaylistRequest(BaseModel):
    """Request to generate smart playlists."""
    playlist_types: List[str] = ["most_played", "recently_added", "never_played"]
    category_fields: List[str] = ["genre", "artist"]
    min_tracks_per_category: int = 3


class SmartPlaylistResponse(BaseModel):
    """Smart playlist generation response."""
    playlists_created: int
    playlist_names: List[str]
    total_tracks_organized: int


@router.post("/check", response_model=IntegrityReport)
async def check_integrity(
    source: str = Query("queue", description="Source to check: queue, ipod, or local"),
    fix_duplicates: bool = Query(False, description="Automatically resolve duplicates"),
    _: None = Depends(verify_api_key)
):
    """Perform comprehensive integrity check on music files."""
    try:
        # Get appropriate repository
        if source == "queue":
            repo = get_queue_repo()
        elif source == "ipod":
            repo = get_ipod_repo()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")
        
        # Get all tracks
        tracks = await repo.get_tracks()
        
        if not tracks:
            return IntegrityReport(
                total_files_checked=0,
                files_with_issues=0,
                duplicate_groups=[],
                corrupted_files=[],
                missing_files=[]
            )
        
        # Check for duplicates
        duplicates = await file_integrity_manager.find_duplicates_in_repository(repo)
        
        # Check file integrity
        corrupted_files = []
        missing_files = []
        
        for track in tracks:
            if not track.file_path:
                continue
                
            # Check if file exists
            from pathlib import Path
            if not Path(track.file_path).exists():
                missing_files.append(track.file_path)
                continue
            
            # Check integrity if hash is available
            if hasattr(track, 'sha1_hash') and track.sha1_hash:
                is_valid = await file_integrity_manager.verify_track_integrity(track)
                if not is_valid:
                    corrupted_files.append(track.file_path)
        
        # Build duplicate groups
        duplicate_groups = []
        total_duplicates = 0
        
        for hash_val, duplicate_tracks in duplicates.items():
            if len(duplicate_tracks) > 1:
                total_duplicates += len(duplicate_tracks) - 1  # Count extras
                
                files = [t.file_path for t in duplicate_tracks if t.file_path]
                total_size = sum(getattr(t, 'file_size', 0) or 0 for t in duplicate_tracks)
                
                duplicate_groups.append(DuplicateGroup(
                    hash=hash_val[:16] + "...",  # Shortened hash
                    files=files,
                    total_size=total_size,
                    suggested_action="keep_highest_quality"
                ))
        
        # Resolve duplicates if requested
        if fix_duplicates and duplicates:
            await duplicate_resolver.resolve_duplicate_tracks(duplicates, repo)
        
        return IntegrityReport(
            total_files_checked=len(tracks),
            files_with_issues=len(corrupted_files) + len(missing_files) + total_duplicates,
            duplicate_groups=duplicate_groups,
            corrupted_files=corrupted_files,
            missing_files=missing_files
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Integrity check failed: {str(e)}")


@router.post("/duplicates/resolve")
async def resolve_duplicates(
    source: str = Query("queue", description="Source to resolve duplicates in"),
    strategy: str = Query("keep_highest_quality", description="Resolution strategy"),
    _: None = Depends(verify_api_key)
):
    """Resolve duplicate files using specified strategy."""
    try:
        # Get appropriate repository
        if source == "queue":
            repo = get_queue_repo()
        elif source == "ipod":
            repo = get_ipod_repo()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")
        
        # Find duplicates
        duplicates = await file_integrity_manager.find_duplicates_in_repository(repo)
        
        if not duplicates:
            return SuccessResponse(
                success=True,
                message="No duplicates found"
            )
        
        # Resolve duplicates
        kept_tracks = await duplicate_resolver.resolve_duplicate_tracks(
            duplicates, repo, strategy
        )
        
        removed_count = sum(len(tracks) for tracks in duplicates.values()) - len(kept_tracks)
        
        return SuccessResponse(
            success=True,
            message=f"Resolved {len(duplicates)} duplicate groups, removed {removed_count} tracks"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Duplicate resolution failed: {str(e)}")


@router.post("/smart-playlists/generate", response_model=SmartPlaylistResponse)
async def generate_smart_playlists(
    request: SmartPlaylistRequest,
    source: str = Query("queue", description="Source repository for playlist generation"),
    _: None = Depends(verify_api_key)
):
    """Generate smart playlists using various algorithms."""
    try:
        # Get appropriate repository
        if source == "queue":
            repo = get_queue_repo()
        elif source == "ipod":
            repo = get_ipod_repo()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")
        
        generator = create_smart_playlist_generator(repo)
        created_playlists = []
        total_tracks = 0
        
        # Generate smart playlists
        if "most_played" in request.playlist_types:
            smart_playlists = await generator.generate_smart_playlists()
            created_playlists.extend(smart_playlists)
        
        # Generate category playlists
        for category_field in request.category_fields:
            category_playlists = await generator.generate_category_playlists(
                category_field, 
                min_tracks=request.min_tracks_per_category
            )
            created_playlists.extend(category_playlists)
        
        # Count total tracks organized
        for playlist in created_playlists:
            total_tracks += len(playlist.track_ids)
        
        # TODO: Save playlists to repository (depends on playlist repository implementation)
        
        return SmartPlaylistResponse(
            playlists_created=len(created_playlists),
            playlist_names=[p.name for p in created_playlists],
            total_tracks_organized=total_tracks
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart playlist generation failed: {str(e)}")


@router.get("/smart-playlists/discovery")
async def generate_discovery_playlist(
    limit: int = Query(30, description="Number of tracks in discovery playlist"),
    source: str = Query("queue", description="Source repository"),
    _: None = Depends(verify_api_key)
):
    """Generate a discovery playlist with variety and underplayed tracks."""
    try:
        # Get appropriate repository
        if source == "queue":
            repo = get_queue_repo()
        elif source == "ipod":
            repo = get_ipod_repo()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")
        
        generator = create_smart_playlist_generator(repo)
        discovery_playlist = await generator.generate_discovery_playlist(limit)
        
        if not discovery_playlist:
            raise HTTPException(status_code=404, detail="No tracks available for discovery playlist")
        
        return {
            "success": True,
            "playlist": {
                "name": discovery_playlist.name,
                "track_count": len(discovery_playlist.track_ids),
                "track_ids": discovery_playlist.track_ids
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery playlist generation failed: {str(e)}")


@router.get("/smart-playlists/workout")
async def generate_workout_playlist(
    limit: int = Query(40, description="Number of tracks in workout playlist"),
    min_bpm: int = Query(120, description="Minimum BPM for energetic tracks"),
    source: str = Query("queue", description="Source repository"),
    _: None = Depends(verify_api_key)
):
    """Generate a high-energy workout playlist based on BPM."""
    try:
        # Get appropriate repository
        if source == "queue":
            repo = get_queue_repo()
        elif source == "ipod":
            repo = get_ipod_repo()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")
        
        generator = create_smart_playlist_generator(repo)
        workout_playlist = await generator.generate_workout_playlist(limit, min_bpm)
        
        if not workout_playlist:
            raise HTTPException(status_code=404, detail="No suitable tracks found for workout playlist")
        
        return {
            "success": True,
            "playlist": {
                "name": workout_playlist.name,
                "track_count": len(workout_playlist.track_ids),
                "track_ids": workout_playlist.track_ids,
                "min_bpm": min_bpm
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workout playlist generation failed: {str(e)}")


@router.post("/hash/update")
async def update_file_hashes(
    source: str = Query("queue", description="Source to update hashes for"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: None = Depends(verify_api_key)
):
    """Update SHA1 hashes for all tracks (runs in background)."""
    
    async def update_hashes_task():
        """Background task to update file hashes."""
        try:
            # Get appropriate repository
            if source == "queue":
                repo = get_queue_repo()
            elif source == "ipod":
                repo = get_ipod_repo()
            else:
                return
            
            tracks = await repo.get_tracks()
            updated_count = 0
            
            for track in tracks:
                if track.file_path:
                    success = await file_integrity_manager.update_track_hash(track)
                    if success:
                        updated_count += 1
            
            return updated_count
            
        except Exception as e:
            # Log error in background task
            import logging
            logging.error(f"Hash update task failed: {e}")
    
    background_tasks.add_task(update_hashes_task)
    
    return SuccessResponse(
        success=True,
        message="Hash update started in background"
    )