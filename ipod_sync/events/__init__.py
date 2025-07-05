"""Event system for loose coupling between components."""
import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Pre-defined event types."""
    TRACK_ADDED = "track_added"
    TRACK_UPDATED = "track_updated"
    TRACK_REMOVED = "track_removed"
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_UPDATED = "playlist_updated"
    PLAYLIST_DELETED = "playlist_deleted"
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    IPOD_CONNECTED = "ipod_connected"
    IPOD_DISCONNECTED = "ipod_disconnected"
    QUEUE_UPDATED = "queue_updated"

@dataclass
class Event:
    """Event data structure."""
    type: EventType
    source: str  # Component that emitted the event
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventBus:
    """Central event bus for application-wide event handling."""
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._async_listeners: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
    
    def on(self, event_type: EventType, callback: Callable[[Event], None]):
        """Register a synchronous event listener."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        self._listeners[event_type].append(callback)
        logger.debug(f"Registered listener for {event_type.value}")
    
    def on_async(self, event_type: EventType, callback: Callable[[Event], None]):
        """Register an asynchronous event listener."""
        if event_type not in self._async_listeners:
            self._async_listeners[event_type] = []
        
        self._async_listeners[event_type].append(callback)
        logger.debug(f"Registered async listener for {event_type.value}")
    
    def off(self, event_type: EventType, callback: Callable):
        """Unregister an event listener."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Unregistered listener for {event_type.value}")
            except ValueError:
                pass
        
        if event_type in self._async_listeners:
            try:
                self._async_listeners[event_type].remove(callback)
                logger.debug(f"Unregistered async listener for {event_type.value}")
            except ValueError:
                pass
    
    def emit(self, event_type: EventType, source: str, data: Dict[str, Any] = None):
        """Emit an event synchronously."""
        event = Event(
            type=event_type,
            source=source,
            data=data or {}
        )
        
        self._store_event(event)
        
        # Call synchronous listeners
        for callback in self._listeners.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event listener for {event_type.value}: {e}")
        
        logger.debug(f"Emitted event {event_type.value} from {source}")
    
    async def emit_async(self, event_type: EventType, source: str, data: Dict[str, Any] = None):
        """Emit an event asynchronously."""
        event = Event(
            type=event_type,
            source=source,
            data=data or {}
        )
        
        self._store_event(event)
        
        # Call synchronous listeners
        for callback in self._listeners.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event listener for {event_type.value}: {e}")
        
        # Call asynchronous listeners
        tasks = []
        for callback in self._async_listeners.get(event_type, []):
            try:
                task = asyncio.create_task(callback(event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating async task for {event_type.value}: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug(f"Emitted async event {event_type.value} from {source}")
    
    def _store_event(self, event: Event):
        """Store event in history."""
        self._event_history.append(event)
        
        # Trim history if needed
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_recent_events(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get recent events, optionally filtered by type."""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        return events[-limit:]
    
    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()

# Global event bus instance
event_bus = EventBus()

# Convenience functions
def emit_track_added(source: str, track_id: str, track_data: Dict[str, Any]):
    """Emit track added event."""
    event_bus.emit(EventType.TRACK_ADDED, source, {
        "track_id": track_id,
        "track": track_data
    })

def emit_sync_started(source: str, queue_size: int):
    """Emit sync started event."""
    event_bus.emit(EventType.SYNC_STARTED, source, {
        "queue_size": queue_size,
        "started_at": datetime.now().isoformat()
    })

def emit_sync_completed(source: str, synced_count: int, duration: float):
    """Emit sync completed event."""
    event_bus.emit(EventType.SYNC_COMPLETED, source, {
        "synced_count": synced_count,
        "duration_seconds": duration,
        "completed_at": datetime.now().isoformat()
    })

async def emit_plugin_loaded(source: str, plugin_id: str, plugin_name: str):
    """Emit plugin loaded event."""
    await event_bus.emit_async(EventType.PLUGIN_LOADED, source, {
        "plugin_id": plugin_id,
        "plugin_name": plugin_name
    })