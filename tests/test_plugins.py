"""Tests for plugin system."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from ipod_sync.plugins import MediaSourcePlugin, MediaItem, PluginStatus
from ipod_sync.plugins.manager import PluginManager
from ipod_sync.plugins.audible_plugin import AudiblePlugin

class MockPlugin(MediaSourcePlugin):
    """Mock plugin for testing."""
    
    @property
    def name(self) -> str:
        return "Test Plugin"
    
    @property
    def identifier(self) -> str:
        return "test"
    
    def is_available(self) -> bool:
        return True
    
    def get_status(self) -> PluginStatus:
        return PluginStatus.AVAILABLE
    
    def authenticate(self) -> bool:
        return True
    
    def is_authenticated(self) -> bool:
        return True
    
    def fetch_library(self) -> List[MediaItem]:
        return [MediaItem(title="Test Item")]
    
    def download_item(self, item_id: str, metadata: Dict[str, Any]) -> str:
        return "/tmp/test.mp3"

class TestPluginManager:
    def test_register_plugin_class(self):
        manager = PluginManager()
        manager.register_plugin_class(MockPlugin)
        assert "test" in manager._plugin_classes
    
    def test_load_plugin(self):
        manager = PluginManager()
        manager.register_plugin_class(MockPlugin)
        assert manager.load_plugin("test") is True
        assert "test" in manager._plugins
    
    def test_get_plugin(self):
        manager = PluginManager()
        manager.register_plugin_class(MockPlugin)
        plugin = manager.get_plugin("test")
        assert isinstance(plugin, MockPlugin)
    
    def test_list_available_plugins(self):
        manager = PluginManager()
        manager.register_plugin_class(MockPlugin)
        plugins = manager.list_available_plugins()
        assert len(plugins) == 1
        assert plugins[0]['identifier'] == 'test'
        assert plugins[0]['name'] == 'Test Plugin'
        assert plugins[0]['available'] is True

class TestAudiblePlugin:
    @patch('shutil.which')
    def test_is_available(self, mock_which):
        mock_which.return_value = "/usr/bin/audible"
        plugin = AudiblePlugin()
        assert plugin.is_available() is True
        
        mock_which.return_value = None
        assert plugin.is_available() is False
    
    @patch('subprocess.run')
    def test_is_authenticated(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        plugin = AudiblePlugin()
        assert plugin.is_authenticated() is True
        
        mock_result.returncode = 1
        assert plugin.is_authenticated() is False
    
    @patch('subprocess.run')
    def test_fetch_library(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''[
            {
                "title": "Test Book",
                "authors": [{"name": "Test Author"}],
                "asin": "B123456789",
                "runtime_length_min": 300
            }
        ]'''
        mock_run.return_value = mock_result
        
        plugin = AudiblePlugin()
        
        # Mock authentication check
        with patch.object(plugin, 'is_authenticated', return_value=True):
            items = plugin.fetch_library()
            
        assert len(items) == 1
        assert items[0].title == "Test Book"
        assert items[0].artist == "Test Author"
        assert items[0].duration == 18000  # 300 minutes * 60 seconds
        assert items[0].category == "audiobook"
    
    @patch('subprocess.run')
    def test_download_item(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        plugin = AudiblePlugin()
        
        # Mock authentication check
        with patch.object(plugin, 'is_authenticated', return_value=True):
            file_path = plugin.download_item("test_id", {
                "asin": "B123456789",
                "title": "Test Book"
            })
        
        assert "B123456789.m4b" in file_path
    
    def test_get_config_schema(self):
        plugin = AudiblePlugin()
        schema = plugin.get_config_schema()
        
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "download_format" in schema["properties"]
        assert "auto_download" in schema["properties"]

class TestMediaItem:
    def test_media_item_creation(self):
        item = MediaItem(
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            duration=180,
            category="music"
        )
        
        assert item.title == "Test Track"
        assert item.artist == "Test Artist"
        assert item.album == "Test Album"
        assert item.duration == 180
        assert item.category == "music"
        assert item.file_path is None
        assert item.metadata is None
    
    def test_media_item_with_metadata(self):
        metadata = {"format": "mp3", "bitrate": 320}
        item = MediaItem(
            title="Test Track",
            metadata=metadata
        )
        
        assert item.metadata == metadata

class TestPluginStatus:
    def test_plugin_status_enum(self):
        assert PluginStatus.AVAILABLE.value == "available"
        assert PluginStatus.UNAVAILABLE.value == "unavailable"
        assert PluginStatus.ERROR.value == "error"