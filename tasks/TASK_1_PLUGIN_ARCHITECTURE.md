# Task 1: Implement Plugin Architecture Foundation

**Priority**: High  
**Estimated Time**: 3-4 days  
**Skills Required**: Python OOP, Abstract Base Classes  
**Assigned to**: _[Developer Name]_

## Overview
Create a plugin system that allows different media sources (Audible, YouTube, podcasts) to be implemented as separate, interchangeable modules. This will make the system extensible and reduce coupling between components.

## Learning Objectives
- Understand Abstract Base Classes and interface design
- Learn plugin architecture patterns
- Practice dependency injection and factory patterns
- Implement dynamic module loading

## Acceptance Criteria
- [ ] Plugin base classes defined with clear interfaces
- [ ] Plugin discovery and loading mechanism
- [ ] At least one existing feature (Audible) converted to plugin
- [ ] Plugin registration system working
- [ ] Unit tests for plugin system with >80% coverage
- [ ] Documentation for plugin developers

## Background Context
This task is inspired by GTKPod's sophisticated plugin system which uses interface-based design to allow features to be loaded/unloaded dynamically. GTKPod has plugins for different file types, UI components, and external services - all using the same base architecture.

## Implementation Steps

### Step 1.1: Create Plugin Base Classes (1 day)

**File**: `ipod_sync/plugins/__init__.py`

```python
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
```

**What to implement:**
1. Review the existing `audible_import.py` to understand current functionality
2. Design the plugin interfaces based on common operations
3. Create the base classes with proper abstract methods
4. Add comprehensive docstrings explaining each method's purpose
5. Consider what configuration each plugin might need

**Testing checklist:**
- [ ] Can instantiate concrete plugin classes
- [ ] Abstract methods raise NotImplementedError when not overridden
- [ ] MediaItem dataclass works correctly
- [ ] PluginStatus enum has correct values

### Step 1.2: Create Plugin Manager (1 day)

**File**: `ipod_sync/plugins/manager.py`

```python
"""Plugin manager for loading and managing media source plugins."""
import importlib
import pkgutil
from typing import Dict, List, Type
import logging
from pathlib import Path

from . import MediaSourcePlugin, PluginStatus

logger = logging.getLogger(__name__)

class PluginManager:
    """Manages loading and registration of media source plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, MediaSourcePlugin] = {}
        self._plugin_classes: Dict[str, Type[MediaSourcePlugin]] = {}
    
    def discover_plugins(self) -> None:
        """Discover and register all available plugins."""
        plugins_dir = Path(__file__).parent
        
        # Look for plugin modules in the plugins directory
        for finder, name, ispkg in pkgutil.iter_modules([str(plugins_dir)]):
            if name.startswith('_') or name == 'manager':
                continue
                
            try:
                module = importlib.import_module(f'ipod_sync.plugins.{name}')
                
                # Look for plugin classes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, MediaSourcePlugin) and 
                        attr != MediaSourcePlugin):
                        
                        self.register_plugin_class(attr)
                        logger.info(f"Discovered plugin: {attr.__name__}")
                        
            except Exception as e:
                logger.error(f"Failed to load plugin module {name}: {e}")
    
    # ... rest of implementation
```

**What to implement:**
1. Study Python's `importlib` and `pkgutil` for dynamic loading
2. Implement plugin discovery that scans the plugins directory
3. Add proper error handling for failed plugin loads
4. Create plugin lifecycle management (load/unload)
5. Add logging for debugging plugin issues

**Key concepts to understand:**
- **Dynamic imports**: How to load Python modules at runtime
- **Reflection**: Using `dir()` and `getattr()` to find classes
- **Error isolation**: Ensuring one bad plugin doesn't break others

**Testing checklist:**
- [ ] Can discover plugins in directory
- [ ] Handles missing dependencies gracefully
- [ ] Loads plugins on demand
- [ ] Returns correct plugin status information

### Step 1.3: Convert Audible Integration to Plugin (1 day)

**File**: `ipod_sync/plugins/audible_plugin.py`

Study the existing `ipod_sync/audible_import.py` file first, then create:

```python
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
    
    # ... implement all abstract methods
```

**What to implement:**
1. **Port existing functionality**: Move code from `audible_import.py`
2. **Implement all interface methods**: Each abstract method must be implemented
3. **Add error handling**: Wrap subprocess calls with proper exception handling
4. **Configuration support**: Define what settings the plugin needs
5. **Library fetching**: Convert existing library fetching to return MediaItem objects

**Migration strategy:**
- Keep existing `audible_import.py` working during development
- Gradually move functions to the plugin
- Update calling code to use plugin manager
- Remove old code only after plugin is fully tested

**Testing checklist:**
- [ ] Plugin loads successfully
- [ ] All interface methods implemented
- [ ] Audible authentication works
- [ ] Library fetching returns correct MediaItem objects
- [ ] Download functionality works
- [ ] Handles missing audible-cli gracefully

### Step 1.4: Integration with Application (0.5 days)

Update the main application to use the plugin system:

**Files to modify:**
- `ipod_sync/app.py` - Add plugin manager initialization
- Remove direct imports of `audible_import`
- Update endpoints to use plugin manager

```python
# In app.py startup
from .plugins.manager import plugin_manager

@app.on_event("startup")
async def startup():
    plugin_manager.discover_plugins()
    logger.info(f"Loaded {len(plugin_manager._plugins)} plugins")
```

**What to implement:**
1. Initialize plugin manager on application startup
2. Update API endpoints to use plugins instead of direct imports
3. Add plugin status endpoints for debugging
4. Ensure backward compatibility during transition

### Step 1.5: Testing and Documentation (0.5 days)

**File**: `tests/test_plugins.py`

Create comprehensive tests covering:

```python
"""Tests for plugin system."""
import pytest
from unittest.mock import Mock, patch
from ipod_sync.plugins import MediaSourcePlugin, MediaItem, PluginStatus
from ipod_sync.plugins.manager import PluginManager
from ipod_sync.plugins.audible_plugin import AudiblePlugin

class MockPlugin(MediaSourcePlugin):
    """Mock plugin for testing."""
    # ... implementation

class TestPluginManager:
    def test_register_plugin_class(self):
        # Test plugin registration
        pass
    
    def test_load_plugin(self):
        # Test plugin loading
        pass
```

**Test coverage requirements:**
- [ ] Plugin manager discovery and loading
- [ ] Audible plugin functionality
- [ ] Error handling scenarios
- [ ] Plugin status reporting
- [ ] Configuration validation

## Troubleshooting Guide

### Common Issues

**Import errors when loading plugins:**
- Check that plugin files have proper `__init__.py` files
- Verify plugin classes inherit from `MediaSourcePlugin`
- Ensure all abstract methods are implemented

**Plugin discovery not finding plugins:**
- Check file naming conventions (no leading underscores)
- Verify plugins directory structure
- Look at logs for import errors

**Audible plugin authentication fails:**
- Check if `audible-cli` is installed and in PATH
- Verify existing authentication status
- Test subprocess calls manually

### Testing Tips

**Mock external dependencies:**
```python
@patch('subprocess.run')
def test_audible_authentication(self, mock_run):
    mock_run.return_value.returncode = 0
    plugin = AudiblePlugin()
    assert plugin.is_authenticated() is True
```

**Test plugin discovery:**
```python
def test_plugin_discovery(self, tmp_path):
    # Create temporary plugin file
    # Test that manager finds it
```

## Success Criteria

When this task is complete, you should have:

1. **Working plugin system** that can discover and load plugins dynamically
2. **Audible plugin** that replaces the existing hardcoded integration
3. **Comprehensive tests** with good coverage
4. **Clear documentation** for future plugin developers
5. **Integration** with the main application that works seamlessly

## Next Steps

After completing this task:
- Task 2 (Repository Pattern) can use plugins as data sources
- Task 3 (API Refactoring) can add plugin management endpoints
- New media source plugins can be added easily

## Resources

- [Python ABC documentation](https://docs.python.org/3/library/abc.html)
- [Plugin architecture patterns](https://python-patterns.guide/gang-of-four/abstract-factory/)
- Existing `audible_import.py` for reference implementation
- GTKPod plugin system (in `docs/gtkpod-master/plugins/`) for inspiration

## Questions for Code Review

1. Are all abstract methods properly implemented in the Audible plugin?
2. Does the plugin manager handle errors gracefully?
3. Is the configuration system flexible enough for different plugin types?
4. Are the tests comprehensive and realistic?
5. Is the plugin interface design future-proof for other media sources?