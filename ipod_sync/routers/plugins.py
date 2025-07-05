"""Plugins API router."""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from .models import PluginResponse, SuccessResponse, PluginActionRequest
from ..plugins.manager import plugin_manager
from ..plugins import MediaItem
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])

@router.get("/", response_model=List[PluginResponse])
async def list_plugins(_: None = Depends(verify_api_key)):
    """List all available plugins."""
    try:
        plugins = plugin_manager.list_available_plugins()
        return [PluginResponse(**plugin) for plugin in plugins]
        
    except Exception as e:
        raise HTTPException(500, f"Failed to list plugins: {str(e)}")

@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin_info(
    plugin_id: str,
    _: None = Depends(verify_api_key)
):
    """Get information about a specific plugin."""
    try:
        plugins = plugin_manager.list_available_plugins()
        for plugin_data in plugins:
            if plugin_data['identifier'] == plugin_id:
                return PluginResponse(**plugin_data)
        
        raise HTTPException(404, f"Plugin {plugin_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get plugin info: {str(e)}")

@router.post("/{plugin_id}/load")
async def load_plugin(
    plugin_id: str,
    _: None = Depends(verify_api_key)
):
    """Load a specific plugin."""
    try:
        success = plugin_manager.load_plugin(plugin_id)
        if not success:
            raise HTTPException(400, f"Failed to load plugin {plugin_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Plugin {plugin_id} loaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to load plugin: {str(e)}")

@router.post("/{plugin_id}/authenticate")
async def authenticate_plugin(
    plugin_id: str,
    _: None = Depends(verify_api_key)
):
    """Authenticate a plugin."""
    try:
        plugin = plugin_manager.get_plugin(plugin_id)
        success = plugin.authenticate()
        
        if not success:
            raise HTTPException(400, f"Authentication failed for plugin {plugin_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Plugin {plugin_id} authenticated successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to authenticate plugin: {str(e)}")

@router.get("/{plugin_id}/library")
async def get_plugin_library(
    plugin_id: str,
    _: None = Depends(verify_api_key)
):
    """Get library content from a plugin."""
    try:
        plugin = plugin_manager.get_plugin(plugin_id)
        
        if not plugin.is_authenticated():
            raise HTTPException(401, f"Plugin {plugin_id} not authenticated")
        
        items = plugin.fetch_library()
        
        # Convert MediaItem objects to dictionaries
        library_data = []
        for item in items:
            library_data.append({
                "title": item.title,
                "artist": item.artist,
                "album": item.album,
                "duration": item.duration,
                "category": item.category,
                "metadata": item.metadata or {}
            })
        
        return {"items": library_data}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to get plugin library: {str(e)}")

@router.post("/{plugin_id}/download")
async def download_from_plugin(
    plugin_id: str,
    request: PluginActionRequest,
    _: None = Depends(verify_api_key)
):
    """Download an item from a plugin."""
    try:
        plugin = plugin_manager.get_plugin(plugin_id)
        
        if not plugin.is_authenticated():
            raise HTTPException(401, f"Plugin {plugin_id} not authenticated")
        
        item_id = request.parameters.get("item_id")
        if not item_id:
            raise HTTPException(400, "item_id required in parameters")
        
        file_path = plugin.download_item(item_id, request.parameters)
        
        return SuccessResponse(
            success=True,
            message=f"Item downloaded successfully",
            data={"file_path": file_path}
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to download from plugin: {str(e)}")

@router.get("/{plugin_id}/config")
async def get_plugin_config_schema(
    plugin_id: str,
    _: None = Depends(verify_api_key)
):
    """Get configuration schema for a plugin."""
    try:
        plugin = plugin_manager.get_plugin(plugin_id)
        schema = plugin.get_config_schema()
        
        return {"schema": schema}
        
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to get plugin config schema: {str(e)}")

@router.post("/{plugin_id}/action")
async def execute_plugin_action(
    plugin_id: str,
    request: PluginActionRequest,
    _: None = Depends(verify_api_key)
):
    """Execute a custom action on a plugin."""
    try:
        plugin = plugin_manager.get_plugin(plugin_id)
        
        # This is a generic action endpoint - plugins can define custom actions
        if hasattr(plugin, 'execute_action'):
            result = plugin.execute_action(request.action, request.parameters)
            return SuccessResponse(
                success=True,
                message=f"Action {request.action} executed successfully",
                data=result
            )
        else:
            raise HTTPException(400, f"Plugin {plugin_id} does not support custom actions")
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to execute plugin action: {str(e)}")