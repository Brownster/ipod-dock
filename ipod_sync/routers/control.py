"""Control API router for playback and sync operations."""
from fastapi import APIRouter, HTTPException, Depends

from .models import SuccessResponse
from ..auth import verify_api_key
from ..playback import SerialPlayback
from .. import sync_from_queue, config

router = APIRouter(prefix="/api/v1/control", tags=["control"])

# Initialize playback controller
playback_controller = SerialPlayback()

@router.post("/playback/{command}")
async def playback_control(
    command: str,
    _: None = Depends(verify_api_key)
):
    """Control iPod playback via serial interface."""
    try:
        if command == "play":
            playback_controller.play_pause()
        elif command == "pause":
            playback_controller.play_pause()
        elif command == "next":
            playback_controller.next_track()
        elif command == "prev":
            playback_controller.prev_track()
        else:
            raise HTTPException(400, f"Invalid command: {command}")
        
        return SuccessResponse(
            success=True,
            message=f"Playback command '{command}' executed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Playback command failed: {str(e)}")

@router.post("/sync")
async def trigger_sync(_: None = Depends(verify_api_key)):
    """Trigger a manual sync of the queue."""
    try:
        sync_from_queue.sync_queue(config.IPOD_DEVICE)
        
        return SuccessResponse(
            success=True,
            message="Sync completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Sync failed: {str(e)}")

@router.get("/status")
async def get_system_status(_: None = Depends(verify_api_key)):
    """Get system status information."""
    try:
        from ..repositories.factory import get_ipod_repo

        repo = get_ipod_repo()
        connected = repo.is_connected()
        
        return {
            "ipod_connected": connected,
            "serial_enabled": config.PLAYBACK_SERIAL_PORT is not None,
            "system": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get system status: {str(e)}")