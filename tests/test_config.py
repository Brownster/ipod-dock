"""Tests for configuration management system."""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

from ipod_sync.config.manager import ConfigManager, Config, ConfigurationError, LogLevel

class TestConfig:
    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.log_level == LogLevel.INFO
        assert config.keep_local_copy is False
        assert config.profile == "default"
        assert config.audio.conversion_format == "mp3"
        assert config.audio.conversion_bitrate == 192
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000
        assert config.serial.port == "/dev/serial0"
        assert config.serial.baudrate == 19200

class TestConfigManager:
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()
    
    def test_config_manager_initialization(self):
        """Test config manager initializes with defaults."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            assert manager.profile == "default"
            assert isinstance(manager.config, Config)
    
    def test_load_configuration_from_file(self):
        """Test loading configuration from JSON file."""
        # Create test config file
        config_data = {
            "log_level": "DEBUG",
            "keep_local_copy": True,
            "audio": {
                "conversion_bitrate": 256,
                "normalize_audio": True
            },
            "server": {
                "port": 9000,
                "api_key": "test_key"
            }
        }
        
        config_file = self.config_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            assert manager.config.log_level == LogLevel.DEBUG
            assert manager.config.keep_local_copy is True
            assert manager.config.audio.conversion_bitrate == 256
            assert manager.config.audio.normalize_audio is True
            assert manager.config.server.port == 9000
            assert manager.config.server.api_key == "test_key"
    
    def test_profile_specific_configuration(self):
        """Test profile-specific configuration loading."""
        # Create base config
        base_config = {"server": {"port": 8000}}
        with open(self.config_dir / "config.json", 'w') as f:
            json.dump(base_config, f)
        
        # Create development profile config
        dev_config = {"server": {"port": 9000}, "log_level": "DEBUG"}
        with open(self.config_dir / "config.development.json", 'w') as f:
            json.dump(dev_config, f)
        
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager(profile="development")
            
            assert manager.config.server.port == 9000  # Profile override
            assert manager.config.log_level == LogLevel.DEBUG
    
    @patch.dict(os.environ, {
        'IPOD_API_KEY': 'env_api_key',
        'IPOD_DEVICE': '/dev/test_device',
        'IPOD_LOG_LEVEL': 'ERROR',
        'IPOD_SERIAL_BAUD': '38400'
    })
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            assert manager.config.server.api_key == "env_api_key"
            assert manager.config.ipod.device_path == "/dev/test_device"
            assert manager.config.log_level == LogLevel.ERROR
            assert manager.config.serial.baudrate == 38400
    
    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            # Should not raise any exceptions
            manager._validate_configuration()
    
    def test_configuration_validation_failure(self):
        """Test configuration validation with invalid values."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            # Set invalid bitrate
            manager.config.audio.conversion_bitrate = 32  # Too low
            
            with pytest.raises(ConfigurationError):
                manager._validate_configuration()
    
    def test_plugin_configuration(self):
        """Test plugin-specific configuration management."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            # Test setting plugin config
            test_config = {"api_key": "test_key", "enabled": True}
            manager.set_plugin_config("test_plugin", test_config)
            
            # Test getting plugin config
            retrieved_config = manager.get_plugin_config("test_plugin")
            assert retrieved_config == test_config
            
            # Test getting non-existent plugin config
            empty_config = manager.get_plugin_config("non_existent")
            assert empty_config == {}
    
    def test_to_dict_export(self):
        """Test configuration export to dictionary."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            config_dict = manager.to_dict()
            
            assert "profile" in config_dict
            assert "audio" in config_dict
            assert "ipod" in config_dict
            assert "server" in config_dict
            assert "serial" in config_dict
            assert config_dict["audio"]["conversion_format"] == "mp3"
            assert config_dict["server"]["host"] == "0.0.0.0"
    
    def test_api_key_masking(self):
        """Test API key is masked in export."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            manager.config.server.api_key = "secret_key"
            
            config_dict = manager.to_dict()
            
            assert config_dict["server"]["api_key"] == "***"
    
    def test_invalid_environment_variables(self):
        """Test handling of invalid environment variables."""
        with patch.dict(os.environ, {'IPOD_SERIAL_BAUD': 'invalid_number'}):
            with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
                # Should not raise an exception, just log a warning
                manager = ConfigManager()
                
                # Should use default value
                assert manager.config.serial.baudrate == 19200

class TestLogLevel:
    def test_log_level_enum(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"

class TestConfigurationError:
    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)