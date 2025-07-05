"""Plugin manager for loading and managing media source plugins."""
import importlib
import pkgutil
from typing import Any, Dict, List, Type
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
    
    def register_plugin_class(self, plugin_class: Type[MediaSourcePlugin]) -> None:
        """Register a plugin class."""
        try:
            plugin_instance = plugin_class()
            identifier = plugin_instance.identifier
            
            if identifier in self._plugin_classes:
                logger.warning(f"Plugin {identifier} already registered, overriding")
            
            self._plugin_classes[identifier] = plugin_class
            logger.info(f"Registered plugin class: {identifier}")
            
        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
    
    def load_plugin(self, identifier: str) -> bool:
        """Load and initialize a specific plugin."""
        if identifier not in self._plugin_classes:
            logger.error(f"Plugin {identifier} not found")
            return False
        
        try:
            plugin_instance = self._plugin_classes[identifier]()
            
            if not plugin_instance.is_available():
                logger.warning(f"Plugin {identifier} dependencies not available")
                return False
            
            self._plugins[identifier] = plugin_instance
            logger.info(f"Loaded plugin: {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {identifier}: {e}")
            return False
    
    def get_plugin(self, identifier: str) -> MediaSourcePlugin:
        """Get a loaded plugin by identifier."""
        if identifier not in self._plugins:
            if not self.load_plugin(identifier):
                raise ValueError(f"Plugin {identifier} not available")
        return self._plugins[identifier]
    
    def list_available_plugins(self) -> List[Dict[str, Any]]:
        """List all discovered plugins with their status."""
        plugins = []
        for identifier, plugin_class in self._plugin_classes.items():
            try:
                plugin = plugin_class()
                plugins.append({
                    'identifier': identifier,
                    'name': plugin.name,
                    'status': plugin.get_status().value,
                    'available': plugin.is_available(),
                    'authenticated': plugin.is_authenticated() if plugin.is_available() else False
                })
            except Exception as e:
                plugins.append({
                    'identifier': identifier,
                    'name': identifier,
                    'status': PluginStatus.ERROR.value,
                    'available': False,
                    'authenticated': False,
                    'error': str(e)
                })
        return plugins

# Global plugin manager instance
plugin_manager = PluginManager()

