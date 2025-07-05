"""Enhanced configuration management system."""
from .manager import config_manager, Config, ConfigurationError

# Export main configuration attributes for backward compatibility
PROJECT_ROOT = config_manager.config.project_root
SYNC_QUEUE_DIR = config_manager.config.sync_queue_dir
UPLOADS_DIR = config_manager.config.uploads_dir
LOG_DIR = config_manager.config.log_dir
IPOD_MOUNT = config_manager.config.ipod.mount_point
IPOD_DEVICE = config_manager.config.ipod.device_path
API_KEY = config_manager.config.server.api_key
SUPPORTED_FORMATS = config_manager.config.audio.supported_formats
KEEP_LOCAL_COPY = config_manager.config.keep_local_copy
PLAYBACK_SERIAL_PORT = config_manager.config.serial.port
PLAYBACK_BAUDRATE = config_manager.config.serial.baudrate

# Create status file path
IPOD_STATUS_FILE = PROJECT_ROOT / "ipod_connected"

__all__ = [
    'config_manager',
    'Config',
    'ConfigurationError',
    'PROJECT_ROOT',
    'SYNC_QUEUE_DIR', 
    'UPLOADS_DIR',
    'LOG_DIR',
    'IPOD_MOUNT',
    'IPOD_DEVICE',
    'API_KEY',
    'SUPPORTED_FORMATS',
    'KEEP_LOCAL_COPY',
    'PLAYBACK_SERIAL_PORT',
    'PLAYBACK_BAUDRATE',
    'IPOD_STATUS_FILE'
]