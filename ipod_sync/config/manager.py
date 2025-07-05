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

        if not self.mount_point.parent.exists():
            try:
                self.mount_point.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                errors.append(
                    f"Mount point parent directory does not exist: {self.mount_point.parent}"
                )

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

        if self.max_upload_size < 1024 * 1024:
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
        errors: List[str] = []

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
        
        # Load profile-specific configuration
        if self.profile != "default":
            profile_config_file = config_dir / f"config.{self.profile}.json"
            if profile_config_file.exists():
                self._load_from_file(profile_config_file)
    
    def _load_from_file(self, config_file: Path):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            # Update configuration
            self._update_config_from_dict(data)
            logger.info(f"Loaded configuration from {config_file}")
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load config from {config_file}: {e}")
    
    def _update_config_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary."""
        # Handle nested configuration
        if "audio" in data:
            for key, value in data["audio"].items():
                if hasattr(self.config.audio, key):
                    setattr(self.config.audio, key, value)
        
        if "ipod" in data:
            for key, value in data["ipod"].items():
                if hasattr(self.config.ipod, key):
                    if key.endswith("_point") or key.endswith("_dir"):
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
            "IPOD_SERVER_PORT": ("server", "port"),
            "IPOD_SERVER_HOST": ("server", "host"),
            "IPOD_LOG_LEVEL": ("", "log_level"),
            "IPOD_KEEP_LOCAL": ("", "keep_local_copy"),
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
            setattr(obj, key, str(value).lower() in ["true", "1", "yes"])
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
            raise ConfigurationError("Configuration validation failed:\n" + "\n".join(errors))
        
        logger.info("Configuration validation passed")
    
    def get_plugin_config(self, plugin_id: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin."""
        return self.config.plugin_configs.get(plugin_id, {})
    
    def set_plugin_config(self, plugin_id: str, config: Dict[str, Any]):
        """Set configuration for a specific plugin."""
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
