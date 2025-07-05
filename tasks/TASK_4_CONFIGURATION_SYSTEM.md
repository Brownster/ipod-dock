# Task 4: Implement Configuration Validation System

**Priority**: Medium  
**Estimated Time**: 1-2 days  
**Skills Required**: Python validation, configuration management  
**Assigned to**: _[Developer Name]_  
**Depends on**: Can be done in parallel with other tasks

## Overview
Create a robust configuration system with validation, environment variable support, and profile management. This replaces the simple `config.py` with a sophisticated system that can handle different deployment environments and validate settings.

## Learning Objectives
- Understand configuration management patterns
- Learn validation strategies and error handling
- Practice environment variable handling
- Implement profile-based configuration
- Design extensible configuration systems

## Acceptance Criteria
- [ ] Configuration validation on startup
- [ ] Environment variable override support
- [ ] Configuration profiles (development, production, testing)
- [ ] Plugin-specific configuration support
- [ ] Configuration validation API endpoint
- [ ] Comprehensive error messages for invalid configurations
- [ ] Backward compatibility with existing config usage

## Background Context
GTKPod has sophisticated configuration management with profiles, validation, and runtime configuration changes. This task adapts those patterns to create a modern configuration system for the iPod-dock project.

## Implementation Steps

### Step 4.1: Create Configuration Data Classes (0.5 days)

**File**: `ipod_sync/config/manager.py`

```python
"""Enhanced configuration management with validation."""
import os
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

@dataclass
class AudioConfig:
    """Audio processing configuration."""
    supported_formats: set = field(default_factory=lambda: {
        ".mp3", ".m4a", ".m4b", ".aac", ".aif", ".aiff", ".wav", ".alac"
    })
    conversion_format: str = "mp3"
    conversion_bitrate: int = 192
    normalize_audio: bool = False
    
    def validate(self) -> List[str]:
        """Validate audio configuration."""
        errors = []
        
        if self.conversion_bitrate < 64 or self.conversion_bitrate > 320:
            errors.append("Audio conversion bitrate must be between 64 and 320 kbps")
        
        if self.conversion_format not in ["mp3", "aac", "m4a"]:
            errors.append(f"Invalid conversion format: {self.conversion_format}")
        
        return errors
    
@dataclass
class IpodConfig:
    """iPod-specific configuration."""
    device_path: str = "/dev/disk/by-label/IPOD"
    mount_point: Path = field(default_factory=lambda: Path.cwd() / "mnt" / "ipod")
    auto_mount: bool = True
    auto_eject: bool = True
    create_sysinfo: bool = True
    
    def validate(self) -> List[str]:
        """Validate iPod configuration."""
        errors = []
        
        # Check if mount point parent exists
        if not self.mount_point.parent.exists():
            errors.append(f"Mount point parent directory does not exist: {self.mount_point.parent}")
        
        return errors
    
@dataclass
class ServerConfig:
    """Web server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: Optional[str] = None
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    
    def validate(self) -> List[str]:
        """Validate server configuration."""
        errors = []
        
        if self.port < 1024 or self.port > 65535:
            errors.append("Server port must be between 1024 and 65535")
        
        if self.max_upload_size < 1024 * 1024:  # 1MB minimum
            errors.append("Max upload size must be at least 1MB")
        
        if self.host not in ["0.0.0.0", "127.0.0.1", "localhost"] and not self.host.startswith("192.168."):
            logger.warning(f"Unusual host configuration: {self.host}")
        
        return errors
    
@dataclass
class SerialConfig:
    """Serial communication configuration."""
    port: str = "/dev/serial0"
    baudrate: int = 19200
    timeout: float = 1.0
    enabled: bool = True
    
    def validate(self) -> List[str]:
        """Validate serial configuration."""
        errors = []
        
        if self.baudrate not in [9600, 19200, 38400, 57600, 115200]:
            errors.append(f"Invalid baudrate: {self.baudrate}")
        
        if self.timeout <= 0 or self.timeout > 10:
            errors.append("Serial timeout must be between 0 and 10 seconds")
        
        return errors

@dataclass
class Config:
    """Main configuration class."""
    # Directories
    project_root: Path = field(default_factory=lambda: Path.cwd())
    sync_queue_dir: Path = field(default_factory=lambda: Path.cwd() / "sync_queue")
    uploads_dir: Path = field(default_factory=lambda: Path.cwd() / "uploads")
    log_dir: Path = field(default_factory=lambda: Path.cwd() / "logs")
    
    # Sub-configurations
    audio: AudioConfig = field(default_factory=AudioConfig)
    ipod: IpodConfig = field(default_factory=IpodConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    serial: SerialConfig = field(default_factory=SerialConfig)
    
    # General settings
    log_level: LogLevel = LogLevel.INFO
    keep_local_copy: bool = False
    profile: str = "default"
    
    # Plugin configurations
    plugin_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Validate entire configuration."""
        errors = []
        
        # Validate sub-configurations
        errors.extend(self.audio.validate())
        errors.extend(self.ipod.validate())
        errors.extend(self.server.validate())
        errors.extend(self.serial.validate())
        
        # Validate directories
        required_dirs = [self.sync_queue_dir, self.uploads_dir, self.log_dir]
        for directory in required_dirs:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                errors.append(f"Cannot create directory {directory}: Permission denied")
        
        return errors
```

**What to implement:**
1. **Study existing config.py**: Understand current configuration structure
2. **Design data classes**: Group related settings logically
3. **Add validation methods**: Each config section should validate itself
4. **Use proper types**: Leverage Python type hints and enums
5. **Consider defaults**: Sensible defaults that work out of the box

**Key concepts:**
- **Dataclasses**: Clean way to define configuration structures
- **Validation**: Each config section validates its own data
- **Type safety**: Use enums and proper types
- **Error collection**: Gather all errors before reporting

### Step 4.2: Implement Configuration Manager (1 day)

Continue in `ipod_sync/config/manager.py`:

```python
class ConfigurationError(Exception):
    """Configuration validation error."""
    pass

class ConfigManager:
    """Manages configuration loading, validation, and environment overrides."""
    
    def __init__(self, profile: str = None):
        self.profile = profile or os.getenv("IPOD_PROFILE", "default")
        self.config = Config()
        self._load_configuration()
        self._apply_environment_overrides()
        self._validate_configuration()
    
    def _load_configuration(self):
        """Load configuration from file if it exists."""
        config_dir = self.config.project_root / "config"
        
        # Load base configuration
        base_config_file = config_dir / "config.json"
        if base_config_file.exists():
            self._load_from_file(base_config_file)
            logger.info(f"Loaded base configuration from {base_config_file}")
        
        # Load profile-specific configuration
        if self.profile != "default":
            profile_config_file = config_dir / f"config.{self.profile}.json"
            if profile_config_file.exists():
                self._load_from_file(profile_config_file)
                logger.info(f"Loaded profile configuration from {profile_config_file}")
    
    def _load_from_file(self, config_file: Path):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            self._update_config_from_dict(data)
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
            raise ConfigurationError(f"Invalid configuration file: {config_file}")
    
    def _update_config_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary."""
        # Handle nested configuration sections
        if "audio" in data:
            for key, value in data["audio"].items():
                if hasattr(self.config.audio, key):
                    if key == "supported_formats" and isinstance(value, list):
                        setattr(self.config.audio, key, set(value))
                    else:
                        setattr(self.config.audio, key, value)
        
        if "ipod" in data:
            for key, value in data["ipod"].items():
                if hasattr(self.config.ipod, key):
                    if key == "mount_point":
                        setattr(self.config.ipod, key, Path(value))
                    else:
                        setattr(self.config.ipod, key, value)
        
        if "server" in data:
            for key, value in data["server"].items():
                if hasattr(self.config.server, key):
                    setattr(self.config.server, key, value)
        
        if "serial" in data:
            for key, value in data["serial"].items():
                if hasattr(self.config.serial, key):
                    setattr(self.config.serial, key, value)
        
        # Handle top-level configuration
        for key, value in data.items():
            if key in ["audio", "ipod", "server", "serial", "plugin_configs"]:
                continue
            if hasattr(self.config, key):
                if key.endswith("_dir") or key == "project_root":
                    setattr(self.config, key, Path(value))
                elif key == "log_level":
                    setattr(self.config, key, LogLevel(value))
                else:
                    setattr(self.config, key, value)
        
        # Handle plugin configurations
        if "plugin_configs" in data:
            self.config.plugin_configs.update(data["plugin_configs"])
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        env_mappings = {
            "IPOD_API_KEY": ("server", "api_key"),
            "IPOD_DEVICE": ("ipod", "device_path"),
            "IPOD_MOUNT": ("ipod", "mount_point"),
            "IPOD_SERIAL_PORT": ("serial", "port"),
            "IPOD_SERIAL_BAUD": ("serial", "baudrate"),
            "IPOD_LOG_LEVEL": ("", "log_level"),
            "IPOD_KEEP_LOCAL": ("", "keep_local_copy"),
            "IPOD_SERVER_PORT": ("server", "port"),
            "IPOD_SERVER_HOST": ("server", "host"),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is None:
                continue
            
            try:
                if section:
                    config_section = getattr(self.config, section)
                    self._set_config_value(config_section, key, value)
                else:
                    self._set_config_value(self.config, key, value)
                
                logger.info(f"Applied environment override: {env_var}")
                
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid environment variable {env_var}={value}: {e}")
    
    def _set_config_value(self, obj, key, value):
        """Set configuration value with type conversion."""
        if key.endswith("_point") or key.endswith("_dir"):
            setattr(obj, key, Path(value))
        elif key in ["baudrate", "port"]:
            setattr(obj, key, int(value))
        elif key in ["auto_mount", "auto_eject", "create_sysinfo", "enabled", "keep_local_copy"]:
            setattr(obj, key, value.lower() in ["true", "1", "yes"])
        elif key == "log_level":
            setattr(obj, key, LogLevel(value.upper()))
        elif key == "timeout":
            setattr(obj, key, float(value))
        else:
            setattr(obj, key, value)
    
    def _validate_configuration(self):
        """Validate configuration and raise errors for critical issues."""
        errors = self.config.validate()
        
        # Additional system-level validations
        if not Path(self.config.ipod.device_path).exists():
            logger.warning(f"iPod device {self.config.ipod.device_path} not found")
        
        if self.config.serial.enabled and not Path(self.config.serial.port).exists():
            logger.warning(f"Serial port {self.config.serial.port} not found")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ConfigurationError(error_msg)
        
        logger.info("Configuration validation passed")
    
    def get_plugin_config(self, plugin_id: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin."""
        return self.config.plugin_configs.get(plugin_id, {})
    
    def set_plugin_config(self, plugin_id: str, config: Dict[str, Any]):
        """Set configuration for a specific plugin."""
        # Validate plugin config if plugin provides schema
        try:
            from ..plugins.manager import plugin_manager
            plugin = plugin_manager.get_plugin(plugin_id)
            errors = plugin.validate_config(config)
            if errors:
                raise ConfigurationError(f"Invalid plugin config for {plugin_id}: {errors}")
        except Exception:
            pass  # Plugin might not be loaded yet
        
        self.config.plugin_configs[plugin_id] = config
    
    def reload_configuration(self):
        """Reload configuration from files."""
        logger.info("Reloading configuration")
        self.__init__(self.profile)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "profile": self.profile,
            "project_root": str(self.config.project_root),
            "sync_queue_dir": str(self.config.sync_queue_dir),
            "uploads_dir": str(self.config.uploads_dir),
            "log_dir": str(self.config.log_dir),
            "log_level": self.config.log_level.value,
            "keep_local_copy": self.config.keep_local_copy,
            "audio": {
                "supported_formats": list(self.config.audio.supported_formats),
                "conversion_format": self.config.audio.conversion_format,
                "conversion_bitrate": self.config.audio.conversion_bitrate,
                "normalize_audio": self.config.audio.normalize_audio,
            },
            "ipod": {
                "device_path": self.config.ipod.device_path,
                "mount_point": str(self.config.ipod.mount_point),
                "auto_mount": self.config.ipod.auto_mount,
                "auto_eject": self.config.ipod.auto_eject,
                "create_sysinfo": self.config.ipod.create_sysinfo,
            },
            "server": {
                "host": self.config.server.host,
                "port": self.config.server.port,
                "api_key": "***" if self.config.server.api_key else None,
                "cors_origins": self.config.server.cors_origins,
                "max_upload_size": self.config.server.max_upload_size,
            },
            "serial": {
                "port": self.config.serial.port,
                "baudrate": self.config.serial.baudrate,
                "timeout": self.config.serial.timeout,
                "enabled": self.config.serial.enabled,
            },
            "plugin_configs": self.config.plugin_configs
        }

# Global configuration manager
config_manager = ConfigManager()
```

**What to implement:**
1. **File loading**: JSON configuration files with inheritance
2. **Environment overrides**: Allow deployment-specific settings
3. **Validation**: Comprehensive validation with helpful error messages
4. **Profile support**: Development, testing, production configurations
5. **Plugin integration**: Allow plugins to have their own configuration

### Step 4.3: Create Configuration Files (0.5 days)

**File**: `config/config.example.json`

```json
{
  "profile": "default",
  "log_level": "INFO",
  "keep_local_copy": false,
  "audio": {
    "supported_formats": [".mp3", ".m4a", ".m4b", ".aac", ".wav", ".flac"],
    "conversion_format": "mp3",
    "conversion_bitrate": 192,
    "normalize_audio": false
  },
  "ipod": {
    "device_path": "/dev/disk/by-label/IPOD",
    "mount_point": "./mnt/ipod",
    "auto_mount": true,
    "auto_eject": true,
    "create_sysinfo": true
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "api_key": null,
    "cors_origins": ["*"],
    "max_upload_size": 104857600
  },
  "serial": {
    "port": "/dev/serial0",
    "baudrate": 19200,
    "timeout": 1.0,
    "enabled": true
  },
  "plugin_configs": {
    "audible": {
      "download_format": "m4b",
      "auto_download": false
    },
    "youtube": {
      "quality": "best",
      "extract_audio": true
    }
  }
}
```

**File**: `config/config.development.json`

```json
{
  "log_level": "DEBUG",
  "server": {
    "port": 8001,
    "cors_origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
  },
  "serial": {
    "enabled": false
  },
  "ipod": {
    "auto_mount": false,
    "device_path": "/tmp/fake_ipod"
  },
  "audio": {
    "conversion_bitrate": 128
  }
}
```

**File**: `config/config.production.json`

```json
{
  "log_level": "WARNING",
  "server": {
    "host": "0.0.0.0",
    "port": 80,
    "cors_origins": ["https://yourdomain.com"]
  },
  "audio": {
    "conversion_bitrate": 256,
    "normalize_audio": true
  },
  "keep_local_copy": true
}
```

**What to implement:**
1. **Base configuration**: Sensible defaults that work out of the box
2. **Development profile**: Debug settings, fake devices for testing
3. **Production profile**: Optimized for deployment
4. **Environment-specific overrides**: Different settings per environment

### Step 4.4: Add Configuration API Endpoints (0.5 days)

**File**: `ipod_sync/routers/config.py`

```python
"""Configuration API router."""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from .models import SuccessResponse
from ..config.manager import config_manager, ConfigurationError
from ..auth import verify_api_key

router = APIRouter(prefix="/api/v1/config", tags=["configuration"])

@router.get("/")
async def get_configuration(_: None = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get current configuration (sensitive values masked)."""
    return config_manager.to_dict()

@router.get("/validate")
async def validate_configuration(_: None = Depends(verify_api_key)) -> SuccessResponse:
    """Validate current configuration."""
    try:
        errors = config_manager.config.validate()
        if errors:
            return SuccessResponse(
                success=False,
                message="Configuration validation failed",
                data={"errors": errors}
            )
        
        return SuccessResponse(
            success=True,
            message="Configuration is valid"
        )
    except Exception as e:
        raise HTTPException(500, f"Validation error: {str(e)}")

@router.post("/reload")
async def reload_configuration(_: None = Depends(verify_api_key)) -> SuccessResponse:
    """Reload configuration from files."""
    try:
        config_manager.reload_configuration()
        return SuccessResponse(
            success=True,
            message="Configuration reloaded successfully"
        )
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
    try:
        config_manager.set_plugin_config(plugin_id, config)
        return SuccessResponse(
            success=True,
            message=f"Configuration updated for plugin {plugin_id}"
        )
    except ConfigurationError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to update plugin configuration: {str(e)}")

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
        "config_files_found": [
            str(f) for f in Path("config").glob("*.json") if f.exists()
        ]
    }
```

## Testing Requirements

**File**: `tests/test_config.py`

```python
"""Tests for configuration management system."""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
import os

from ipod_sync.config.manager import ConfigManager, Config, ConfigurationError, LogLevel

class TestConfig:
    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.log_level == LogLevel.INFO
        assert config.keep_local_copy is False
        assert config.audio.conversion_format == "mp3"
        assert config.server.port == 8000

class TestConfigManager:
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir()
    
    def test_load_configuration_from_file(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "log_level": "DEBUG",
            "audio": {"conversion_bitrate": 256},
            "server": {"port": 9000}
        }
        
        config_file = self.config_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            assert manager.config.log_level == LogLevel.DEBUG
            assert manager.config.audio.conversion_bitrate == 256
            assert manager.config.server.port == 9000
    
    @patch.dict(os.environ, {'IPOD_API_KEY': 'test_key', 'IPOD_LOG_LEVEL': 'ERROR'})
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            
            assert manager.config.server.api_key == "test_key"
            assert manager.config.log_level == LogLevel.ERROR
    
    def test_configuration_validation_failure(self):
        """Test configuration validation with invalid values."""
        with patch('ipod_sync.config.manager.Path.cwd', return_value=self.temp_dir):
            manager = ConfigManager()
            manager.config.audio.conversion_bitrate = 32  # Invalid
            
            with pytest.raises(ConfigurationError):
                manager._validate_configuration()
```

## Migration Strategy

### Phase 1: Parallel Implementation
1. Create new configuration system alongside old `config.py`
2. Import both systems during transition
3. Test new system thoroughly

### Phase 2: Gradual Migration
1. Update modules one by one to use new config manager
2. Add deprecation warnings for old config usage
3. Ensure all environment variables still work

### Phase 3: Cleanup
1. Remove old `config.py`
2. Update all documentation
3. Ensure all tests use new system

## Troubleshooting Guide

### Common Issues

**Configuration validation fails:**
- Check JSON syntax in config files
- Verify all required directories exist
- Check environment variable values

**Environment variables not working:**
- Ensure variable names match expected pattern (`IPOD_*`)
- Check variable value types (string, boolean, int)
- Verify environment variables are set before app starts

**Profile loading issues:**
- Check profile file exists
- Verify profile name matches environment variable
- Ensure profile inherits from base configuration

## Success Criteria

When this task is complete, you should have:

1. **Robust configuration system** with validation and error reporting
2. **Environment variable support** for all major settings
3. **Profile-based configuration** for different environments
4. **Plugin configuration support** for extensible settings
5. **Configuration API** for runtime inspection and debugging
6. **Comprehensive tests** covering all configuration scenarios
7. **Backward compatibility** with existing configuration usage

## Next Steps

After completing this task:
- All other tasks can use the enhanced configuration system
- Deployment becomes easier with environment variable support
- Plugin developers can define their own configuration schemas
- System administrators can validate configurations before deployment

## Resources

- [Pydantic for validation](https://pydantic-docs.helpmanual.io/)
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Environment variable best practices](https://12factor.net/config)
- Existing `config.py` for current configuration structure

## Questions for Code Review

1. Are all current configuration options covered?
2. Is the validation comprehensive enough?
3. Are environment variable names consistent and clear?
4. Do the configuration profiles cover expected use cases?
5. Is the migration strategy safe and backward compatible?
6. Are error messages helpful for troubleshooting?