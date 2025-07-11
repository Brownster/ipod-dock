"""Configuration API router."""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from .models import SuccessResponse
from ..config.manager import config_manager, ConfigurationError
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/config", tags=["configuration"])

@router.get("/")
async def get_configuration(_: None = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get current configuration."""
    return config_manager.to_dict()

@router.get("/validate")
async def validate_configuration(_: None = Depends(verify_api_key)) -> SuccessResponse:
    """Validate current configuration."""
    try:
        config_manager._validate_configuration()
        return SuccessResponse(
            success=True,
            message="Configuration is valid"
        )
    except ConfigurationError as e:
        raise HTTPException(400, str(e))

@router.post("/reload")
async def reload_configuration(_: None = Depends(verify_api_key)) -> SuccessResponse:
    """Reload configuration from files."""
    try:
        config_manager.reload_configuration()
        return SuccessResponse(success=True, message="Configuration reloaded successfully")
    except ConfigurationError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to reload configuration: {str(e)}")

@router.get("/plugins/{plugin_id}")
async def get_plugin_configuration(
    plugin_id: str,
    _: None = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Get configuration for a specific plugin."""
    return config_manager.get_plugin_config(plugin_id)

@router.put("/plugins/{plugin_id}")
async def set_plugin_configuration(
    plugin_id: str,
    config: Dict[str, Any],
    _: None = Depends(verify_api_key)
) -> SuccessResponse:
    """Set configuration for a specific plugin."""
    config_manager.set_plugin_config(plugin_id, config)
    return SuccessResponse(
        success=True,
        message=f"Configuration updated for plugin {plugin_id}"
    )

@router.get("/environment")
async def get_environment_info(_: None = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get environment information for debugging."""
    import os
    import sys
    from pathlib import Path

    env_vars = {k: v for k, v in os.environ.items() if k.startswith("IPOD_")}

    return {
        "profile": config_manager.profile,
        "python_version": sys.version,
        "working_directory": str(Path.cwd()),
        "environment_variables": env_vars,
        "config_files_found": [str(f) for f in Path("config").glob("*.json") if f.exists()],
    }
