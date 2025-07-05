"""Plugin system for ipod-sync media sources."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PluginStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable" 
    ERROR = "error"

@dataclass
class MediaItem:
    """Represents a media item from any source."""
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None  # seconds
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    category: str = "music"  # music, audiobook, podcast

class MediaSourcePlugin(ABC):
    """Base class for all media source plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin name."""
        pass
    
    @property
    @abstractmethod
    def identifier(self) -> str:
        """Unique plugin identifier (lowercase, no spaces)."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if plugin dependencies are available."""
        pass
    
    @abstractmethod
    def get_status(self) -> PluginStatus:
        """Get current plugin status."""
        pass
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Perform any required authentication. Return True if successful."""
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if plugin is authenticated and ready to use."""
        pass
    
    @abstractmethod
    def fetch_library(self) -> List[MediaItem]:
        """Fetch available media items from this source."""
        pass
    
    @abstractmethod
    def download_item(self, item_id: str, metadata: Dict[str, Any]) -> str:
        """Download an item and return the file path."""
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for plugin configuration."""
        return {}
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate plugin configuration. Return list of error messages."""
        return []

