"""Audible plugin for ipod-sync."""
import subprocess
import json
import shutil
from typing import List, Dict, Any
from pathlib import Path

from . import MediaSourcePlugin, MediaItem, PluginStatus
from .. import config

class AudiblePlugin(MediaSourcePlugin):
    """Plugin for Audible audiobook integration."""
    
    @property
    def name(self) -> str:
        return "Audible"
    
    @property 
    def identifier(self) -> str:
        return "audible"
    
    def is_available(self) -> bool:
        """Check if audible-cli is installed."""
        return shutil.which("audible") is not None
    
    def get_status(self) -> PluginStatus:
        if not self.is_available():
            return PluginStatus.UNAVAILABLE
        if not self.is_authenticated():
            return PluginStatus.AVAILABLE
        return PluginStatus.AVAILABLE
    
    def authenticate(self) -> bool:
        """Run audible quickstart for authentication."""
        try:
            result = subprocess.run(
                ["audible", "quickstart"], 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def is_authenticated(self) -> bool:
        """Check if audible-cli is authenticated."""
        try:
            result = subprocess.run(
                ["audible", "library", "list", "--count", "1"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def fetch_library(self) -> List[MediaItem]:
        """Fetch Audible library."""
        if not self.is_authenticated():
            raise RuntimeError("Audible plugin not authenticated")
        
        try:
            result = subprocess.run(
                ["audible", "library", "export", "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Failed to fetch library: {result.stderr}")
            
            library_data = json.loads(result.stdout)
            items = []
            
            for book in library_data:
                item = MediaItem(
                    title=book.get("title", "Unknown"),
                    artist=book.get("authors", [{}])[0].get("name") if book.get("authors") else None,
                    album=book.get("series", {}).get("name") if book.get("series") else None,
                    duration=book.get("runtime_length_min", 0) * 60 if book.get("runtime_length_min") else None,
                    metadata={
                        "asin": book.get("asin"),
                        "purchase_date": book.get("purchase_date"),
                        "format": book.get("format_type"),
                        "language": book.get("language")
                    },
                    category="audiobook"
                )
                items.append(item)
            
            return items
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"Failed to fetch Audible library: {e}")
    
    def download_item(self, item_id: str, metadata: Dict[str, Any]) -> str:
        """Download an audiobook and return the file path."""
        if not self.is_authenticated():
            raise RuntimeError("Audible plugin not authenticated")
        
        asin = metadata.get("asin")
        if not asin:
            raise ValueError("ASIN required in metadata")
        
        title = metadata.get("title", "Unknown")
        
        # Create download directory
        downloads_dir = config.SYNC_QUEUE_DIR / "audiobook"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = downloads_dir / f"{asin}.m4b"
        
        try:
            # Download using audible-cli
            result = subprocess.run([
                "audible", "download",
                "--asin", asin,
                "--output-dir", str(downloads_dir),
                "--output-format", "m4b"
            ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            if result.returncode != 0:
                raise RuntimeError(f"Download failed: {result.stderr}")
            
            return str(output_file)
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"Failed to download {title}: {e}")
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for Audible plugin."""
        return {
            "type": "object",
            "properties": {
                "download_format": {
                    "type": "string",
                    "enum": ["m4b", "mp3"],
                    "default": "m4b",
                    "description": "Preferred download format",
                },
                "auto_download": {
                    "type": "boolean",
                    "default": False,
                    "description": "Automatically download new purchases",
                },
            },
        }

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate plugin configuration and return a list of errors."""
        errors: List[str] = []
        fmt = config.get("download_format")
        if fmt and fmt not in {"m4b", "mp3"}:
            errors.append("download_format must be 'm4b' or 'mp3'")
        return errors

