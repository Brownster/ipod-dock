# Task 5: Implement Event System for Loose Coupling

**Priority**: Low  
**Estimated Time**: 1-2 days  
**Skills Required**: Observer pattern, Python async programming  
**Assigned to**: _[Developer Name]_  
**Depends on**: Can be done after other tasks are started

## Overview
Create an event system that allows different components to communicate without tight coupling, similar to GTKPod's signal system. This enables plugins, repositories, and other components to react to events without direct dependencies.

## Learning Objectives
- Understand the Observer design pattern
- Learn publish/subscribe communication patterns
- Practice async programming with Python
- Implement event-driven architecture
- Design extensible communication systems

## Acceptance Criteria
- [ ] Event bus implementation with async support
- [ ] Pre-defined events for common operations
- [ ] Event listeners can be registered/unregistered dynamically
- [ ] Integration with repositories and plugins
- [ ] Event logging for debugging
- [ ] Event history and replay capabilities
- [ ] Performance optimization for high-frequency events

## Background Context
GTKPod uses an extensive signal system for communication between UI components, plugins, and data layers. This allows features to be added without modifying existing code - they simply listen for relevant events and react accordingly.

## Implementation Steps

### Step 5.1: Create Event System Core (1 day)

**File**: `ipod_sync/events/__init__.py`

```python
"""Event system for loose coupling between components."""
import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import weakref
import inspect

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Pre-defined event types for common operations."""
    # Track events
    TRACK_ADDED = "track_added"
    TRACK_UPDATED = "track_updated"
    TRACK_REMOVED = "track_removed"
    TRACK_PLAYED = "track_played"
    
    # Playlist events
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_UPDATED = "playlist_updated"
    PLAYLIST_DELETED = "playlist_deleted"
    
    # Sync events
    SYNC_STARTED = "sync_started"
    SYNC_PROGRESS = "sync_progress"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    
    # Plugin events
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ERROR = "plugin_error"
    
    # System events
    IPOD_CONNECTED = "ipod_connected"
    IPOD_DISCONNECTED = "ipod_disconnected"
    QUEUE_UPDATED = "queue_updated"
    CONFIG_CHANGED = "config_changed"
    
    # Custom events (for plugins)
    CUSTOM = "custom"

@dataclass
class Event:
    """Event data structure."""
    type: EventType
    source: str  # Component that emitted the event
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For tracking related events
    
    def __post_init__(self):
        """Ensure timestamp is set."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventListener:
    """Wrapper for event listener callbacks."""
    
    def __init__(self, callback: Callable, is_async: bool = False, weak_ref: bool = True):
        self.is_async = is_async
        self.weak_ref = weak_ref
        
        if weak_ref and hasattr(callback, '__self__'):
            # Use weak reference for bound methods to prevent memory leaks
            self._callback_ref = weakref.WeakMethod(callback)
        elif weak_ref:
            # Use weak reference for functions
            self._callback_ref = weakref.ref(callback)
        else:
            # Direct reference (be careful of memory leaks)
            self._callback_ref = lambda: callback
    
    def get_callback(self) -> Optional[Callable]:
        """Get the callback function if it still exists."""
        if self.weak_ref:
            return self._callback_ref()
        else:
            return self._callback_ref()
    
    def is_valid(self) -> bool:
        """Check if the callback is still valid."""
        return self.get_callback() is not None

class EventBus:
    """Central event bus for application-wide event handling."""
    
    def __init__(self, max_history: int = 1000):
        self._listeners: Dict[EventType, List[EventListener]] = {}
        self._event_history: List[Event] = []
        self._max_history = max_history
        self._stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "listeners_called": 0,
            "errors": 0
        }
    
    def on(self, 
           event_type: EventType, 
           callback: Callable[[Event], None],
           weak_ref: bool = True) -> None:
        """Register a synchronous event listener."""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        is_async = inspect.iscoroutinefunction(callback)
        listener = EventListener(callback, is_async=is_async, weak_ref=weak_ref)
        
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        self._listeners[event_type].append(listener)
        logger.debug(f"Registered {'async' if is_async else 'sync'} listener for {event_type.value}")
    
    def off(self, event_type: EventType, callback: Callable) -> bool:
        """Unregister an event listener."""
        if event_type not in self._listeners:
            return False
        
        listeners = self._listeners[event_type]
        for i, listener in enumerate(listeners):
            listener_callback = listener.get_callback()
            if listener_callback == callback:
                listeners.pop(i)
                logger.debug(f"Unregistered listener for {event_type.value}")
                return True
        
        return False
    
    def emit(self, 
             event_type: EventType, 
             source: str, 
             data: Dict[str, Any] = None,
             correlation_id: str = None) -> None:
        """Emit an event synchronously."""
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
            correlation_id=correlation_id
        )
        
        self._store_event(event)
        self._stats["events_emitted"] += 1
        
        # Clean up dead listeners first
        self._cleanup_listeners(event_type)
        
        # Call listeners
        listeners = self._listeners.get(event_type, [])
        for listener in listeners:
            try:
                callback = listener.get_callback()
                if callback:
                    if listener.is_async:
                        # Schedule async callback
                        try:
                            loop = asyncio.get_event_loop()
                            loop.create_task(callback(event))
                        except RuntimeError:
                            # No event loop running, skip async callback
                            logger.warning(f"Skipping async callback for {event_type.value} - no event loop")
                    else:
                        # Call sync callback immediately
                        callback(event)
                    
                    self._stats["listeners_called"] += 1
                    
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Error in event listener for {event_type.value}: {e}", exc_info=True)
        
        self._stats["events_processed"] += 1
        logger.debug(f"Emitted event {event_type.value} from {source}")
    
    async def emit_async(self, 
                        event_type: EventType, 
                        source: str, 
                        data: Dict[str, Any] = None,
                        correlation_id: str = None) -> None:
        """Emit an event asynchronously."""
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
            correlation_id=correlation_id
        )
        
        self._store_event(event)
        self._stats["events_emitted"] += 1
        
        # Clean up dead listeners first
        self._cleanup_listeners(event_type)
        
        # Collect all callbacks
        sync_callbacks = []
        async_callbacks = []
        
        listeners = self._listeners.get(event_type, [])
        for listener in listeners:
            callback = listener.get_callback()
            if callback:
                if listener.is_async:
                    async_callbacks.append(callback)
                else:
                    sync_callbacks.append(callback)
        
        # Call sync callbacks
        for callback in sync_callbacks:
            try:
                callback(event)
                self._stats["listeners_called"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Error in sync event listener for {event_type.value}: {e}")
        
        # Call async callbacks concurrently
        if async_callbacks:
            tasks = []
            for callback in async_callbacks:
                try:
                    task = asyncio.create_task(callback(event))
                    tasks.append(task)
                except Exception as e:
                    self._stats["errors"] += 1
                    logger.error(f"Error creating async task for {event_type.value}: {e}")
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self._stats["errors"] += 1
                        logger.error(f"Error in async event listener for {event_type.value}: {result}")
                    else:
                        self._stats["listeners_called"] += 1
        
        self._stats["events_processed"] += 1
        logger.debug(f"Emitted async event {event_type.value} from {source}")
    
    def _cleanup_listeners(self, event_type: EventType) -> None:
        """Remove dead weak references."""
        if event_type not in self._listeners:
            return
        
        valid_listeners = []
        for listener in self._listeners[event_type]:
            if listener.is_valid():
                valid_listeners.append(listener)
        
        self._listeners[event_type] = valid_listeners
    
    def _store_event(self, event: Event) -> None:
        """Store event in history."""
        self._event_history.append(event)
        
        # Trim history if needed
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_recent_events(self, 
                         event_type: Optional[EventType] = None, 
                         limit: int = 100,
                         source: Optional[str] = None,
                         correlation_id: Optional[str] = None) -> List[Event]:
        """Get recent events with optional filtering."""
        events = self._event_history
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if source:
            events = [e for e in events if e.source == source]
        
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]
        
        return events[-limit:] if limit else events
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        logger.debug("Event history cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "active_listeners": sum(len(listeners) for listeners in self._listeners.values()),
            "event_types": list(self._listeners.keys()),
            "history_size": len(self._event_history)
        }
    
    def get_listener_count(self, event_type: EventType) -> int:
        """Get number of listeners for an event type."""
        self._cleanup_listeners(event_type)
        return len(self._listeners.get(event_type, []))

# Global event bus instance
event_bus = EventBus()

# Convenience functions for common events
def emit_track_added(source: str, track_id: str, track_data: Dict[str, Any], correlation_id: str = None):
    """Emit track added event."""
    event_bus.emit(EventType.TRACK_ADDED, source, {
        "track_id": track_id,
        "track": track_data
    }, correlation_id)

def emit_sync_started(source: str, queue_size: int, correlation_id: str = None):
    """Emit sync started event."""
    event_bus.emit(EventType.SYNC_STARTED, source, {
        "queue_size": queue_size,
        "started_at": datetime.now().isoformat()
    }, correlation_id)

def emit_sync_progress(source: str, completed: int, total: int, correlation_id: str = None):
    """Emit sync progress event."""
    event_bus.emit(EventType.SYNC_PROGRESS, source, {
        "completed": completed,
        "total": total,
        "percentage": (completed / total * 100) if total > 0 else 0
    }, correlation_id)

def emit_sync_completed(source: str, synced_count: int, duration: float, correlation_id: str = None):
    """Emit sync completed event."""
    event_bus.emit(EventType.SYNC_COMPLETED, source, {
        "synced_count": synced_count,
        "duration_seconds": duration,
        "completed_at": datetime.now().isoformat()
    }, correlation_id)

async def emit_plugin_loaded(source: str, plugin_id: str, plugin_name: str, correlation_id: str = None):
    """Emit plugin loaded event."""
    await event_bus.emit_async(EventType.PLUGIN_LOADED, source, {
        "plugin_id": plugin_id,
        "plugin_name": plugin_name
    }, correlation_id)

def emit_ipod_connected(source: str, device_path: str, correlation_id: str = None):
    """Emit iPod connected event."""
    event_bus.emit(EventType.IPOD_CONNECTED, source, {
        "device_path": device_path,
        "connected_at": datetime.now().isoformat()
    }, correlation_id)

def emit_custom_event(source: str, event_name: str, data: Dict[str, Any], correlation_id: str = None):
    """Emit a custom event (for plugins)."""
    event_bus.emit(EventType.CUSTOM, source, {
        "event_name": event_name,
        **data
    }, correlation_id)
```

**What to implement:**
1. **Study existing communication patterns**: Look at how components currently interact
2. **Design event types**: Define events that capture important system operations
3. **Implement Observer pattern**: Clean publish/subscribe mechanism
4. **Add async support**: Handle both sync and async event listeners
5. **Memory management**: Use weak references to prevent memory leaks
6. **Performance optimization**: Efficient event processing for high-frequency events

**Key concepts:**
- **Observer pattern**: Decoupled communication between components
- **Weak references**: Prevent memory leaks with automatic cleanup
- **Async programming**: Non-blocking event processing
- **Event correlation**: Track related events across system

### Step 5.2: Integration with Repositories (0.5 days)

Update repository implementations to emit events:

**File**: `ipod_sync/repositories/base_repository.py`

```python
"""Base repository with event integration."""
from abc import ABC
from typing import Any
import uuid

from ..events import event_bus, EventType

class EventEmittingRepository(ABC):
    """Base class for repositories that emit events."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    def _emit_track_event(self, event_type: EventType, track_id: str, track_data: dict = None):
        """Emit a track-related event."""
        correlation_id = str(uuid.uuid4())
        event_bus.emit(event_type, self.source_name, {
            "track_id": track_id,
            "track": track_data or {}
        }, correlation_id)
    
    def _emit_playlist_event(self, event_type: EventType, playlist_id: str, playlist_data: dict = None):
        """Emit a playlist-related event."""
        correlation_id = str(uuid.uuid4())
        event_bus.emit(event_type, self.source_name, {
            "playlist_id": playlist_id,
            "playlist": playlist_data or {}
        }, correlation_id)
```

**Update repository implementations:**

```python
# In IpodRepository.add_track()
def add_track(self, track: Track) -> str:
    # ... existing implementation
    track_id = str(gpod_track.dbid)
    
    # Emit event
    self._emit_track_event(EventType.TRACK_ADDED, track_id, {
        "title": track.title,
        "artist": track.artist,
        "category": track.category
    })
    
    return track_id

# In QueueRepository.add_track()
def add_track(self, track: Track) -> str:
    # ... existing implementation
    file_id = str(dest_path.relative_to(self.queue_dir))
    
    # Emit event
    self._emit_track_event(EventType.QUEUE_UPDATED, file_id, {
        "title": track.title,
        "category": track.category,
        "action": "added"
    })
    
    return file_id
```

### Step 5.3: Event-Driven Features (0.5 days)

Implement useful event-driven features:

**File**: `ipod_sync/events/listeners.py`

```python
"""Built-in event listeners for common operations."""
import logging
from typing import Dict, Any

from . import Event, EventType, event_bus

logger = logging.getLogger(__name__)

class LoggingListener:
    """Logs all events for debugging."""
    
    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
        
        # Register for all event types
        for event_type in EventType:
            event_bus.on(event_type, self.log_event, weak_ref=False)
    
    def log_event(self, event: Event):
        """Log an event."""
        logger.log(self.log_level, 
            f"Event: {event.type.value} from {event.source} "
            f"with data: {event.data}")

class StatisticsCollector:
    """Collects statistics about system usage."""
    
    def __init__(self):
        self.stats = {
            "tracks_added": 0,
            "tracks_removed": 0,
            "syncs_completed": 0,
            "syncs_failed": 0,
            "plugins_loaded": 0
        }
        
        # Register for relevant events
        event_bus.on(EventType.TRACK_ADDED, self.on_track_added, weak_ref=False)
        event_bus.on(EventType.TRACK_REMOVED, self.on_track_removed, weak_ref=False)
        event_bus.on(EventType.SYNC_COMPLETED, self.on_sync_completed, weak_ref=False)
        event_bus.on(EventType.SYNC_FAILED, self.on_sync_failed, weak_ref=False)
        event_bus.on(EventType.PLUGIN_LOADED, self.on_plugin_loaded, weak_ref=False)
    
    def on_track_added(self, event: Event):
        self.stats["tracks_added"] += 1
    
    def on_track_removed(self, event: Event):
        self.stats["tracks_removed"] += 1
    
    def on_sync_completed(self, event: Event):
        self.stats["syncs_completed"] += 1
    
    def on_sync_failed(self, event: Event):
        self.stats["syncs_failed"] += 1
    
    def on_plugin_loaded(self, event: Event):
        self.stats["plugins_loaded"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()

class CacheInvalidator:
    """Invalidates caches when data changes."""
    
    def __init__(self):
        # Register for data change events
        event_bus.on(EventType.TRACK_ADDED, self.invalidate_track_cache, weak_ref=False)
        event_bus.on(EventType.TRACK_UPDATED, self.invalidate_track_cache, weak_ref=False)
        event_bus.on(EventType.TRACK_REMOVED, self.invalidate_track_cache, weak_ref=False)
        event_bus.on(EventType.PLAYLIST_CREATED, self.invalidate_playlist_cache, weak_ref=False)
        event_bus.on(EventType.PLAYLIST_UPDATED, self.invalidate_playlist_cache, weak_ref=False)
        event_bus.on(EventType.PLAYLIST_DELETED, self.invalidate_playlist_cache, weak_ref=False)
    
    def invalidate_track_cache(self, event: Event):
        # Invalidate track-related caches
        logger.debug("Invalidating track cache due to event")
        # Implementation would clear actual caches
    
    def invalidate_playlist_cache(self, event: Event):
        # Invalidate playlist-related caches
        logger.debug("Invalidating playlist cache due to event")
        # Implementation would clear actual caches

# Initialize built-in listeners
def initialize_builtin_listeners():
    """Initialize built-in event listeners."""
    global _logging_listener, _stats_collector, _cache_invalidator
    
    _logging_listener = LoggingListener(logging.DEBUG)
    _stats_collector = StatisticsCollector()
    _cache_invalidator = CacheInvalidator()
    
    logger.info("Initialized built-in event listeners")

# Global instances
_logging_listener = None
_stats_collector = None
_cache_invalidator = None

def get_statistics_collector() -> StatisticsCollector:
    """Get the global statistics collector."""
    if _stats_collector is None:
        initialize_builtin_listeners()
    return _stats_collector
```

## Testing Requirements

**File**: `tests/test_events.py`

```python
"""Tests for event system."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from ipod_sync.events import EventBus, Event, EventType, emit_track_added

class TestEvent:
    def test_event_creation(self):
        """Test Event dataclass creation."""
        event = Event(
            type=EventType.TRACK_ADDED,
            source="test_component",
            data={"track_id": "123", "title": "Test Track"}
        )
        
        assert event.type == EventType.TRACK_ADDED
        assert event.source == "test_component"
        assert event.data["track_id"] == "123"
        assert isinstance(event.timestamp, datetime)

class TestEventBus:
    def setup_method(self):
        """Set up test environment."""
        self.event_bus = EventBus()
    
    def test_register_sync_listener(self):
        """Test registering synchronous event listener."""
        mock_callback = Mock()
        
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        
        # Emit event and verify callback was called
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {"track_id": "123"})
        
        mock_callback.assert_called_once()
        event = mock_callback.call_args[0][0]
        assert event.type == EventType.TRACK_ADDED
        assert event.data["track_id"] == "123"
    
    @pytest.mark.asyncio
    async def test_register_async_listener(self):
        """Test registering asynchronous event listener."""
        mock_callback = AsyncMock()
        
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        
        # Emit event asynchronously
        await self.event_bus.emit_async(EventType.TRACK_ADDED, "test", {"track_id": "123"})
        
        mock_callback.assert_called_once()
    
    def test_unregister_listener(self):
        """Test unregistering event listener."""
        mock_callback = Mock()
        
        # Register and then unregister
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        success = self.event_bus.off(EventType.TRACK_ADDED, mock_callback)
        
        assert success is True
        
        # Emit event - callback should not be called
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        mock_callback.assert_not_called()
    
    def test_event_history(self):
        """Test event history storage and retrieval."""
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {"track_id": "123"})
        self.event_bus.emit(EventType.SYNC_STARTED, "test", {"queue_size": 5})
        
        # Get all events
        all_events = self.event_bus.get_recent_events()
        assert len(all_events) == 2
        
        # Filter by event type
        track_events = self.event_bus.get_recent_events(EventType.TRACK_ADDED)
        assert len(track_events) == 1
        assert track_events[0].type == EventType.TRACK_ADDED
    
    def test_weak_references(self):
        """Test that weak references work correctly."""
        class TestListener:
            def __init__(self):
                self.called = False
            
            def callback(self, event):
                self.called = True
        
        listener = TestListener()
        self.event_bus.on(EventType.TRACK_ADDED, listener.callback)
        
        # Emit event - should work
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        assert listener.called is True
        
        # Delete listener object
        listener_ref = listener
        del listener
        
        # Force cleanup and emit again - should not crash
        self.event_bus._cleanup_listeners(EventType.TRACK_ADDED)
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
    
    def test_error_handling(self):
        """Test that errors in listeners don't break event system."""
        def failing_callback(event):
            raise Exception("Test exception")
        
        good_callback = Mock()
        
        self.event_bus.on(EventType.TRACK_ADDED, failing_callback, weak_ref=False)
        self.event_bus.on(EventType.TRACK_ADDED, good_callback, weak_ref=False)
        
        # Should not raise exception
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        
        # Good callback should still be called
        good_callback.assert_called_once()
        
        # Error should be tracked in stats
        stats = self.event_bus.get_stats()
        assert stats["errors"] > 0
    
    def test_correlation_id(self):
        """Test correlation ID tracking."""
        correlation_id = "test-correlation-123"
        
        self.event_bus.emit(EventType.SYNC_STARTED, "test", {}, correlation_id)
        self.event_bus.emit(EventType.SYNC_COMPLETED, "test", {}, correlation_id)
        
        # Get events by correlation ID
        related_events = self.event_bus.get_recent_events(correlation_id=correlation_id)
        assert len(related_events) == 2
        assert all(e.correlation_id == correlation_id for e in related_events)
```

## Integration Examples

### Plugin Integration
```python
# In plugin implementation
class MyPlugin(MediaSourcePlugin):
    def __init__(self):
        # Listen for relevant events
        event_bus.on(EventType.TRACK_ADDED, self.on_track_added)
        event_bus.on(EventType.CUSTOM, self.on_custom_event)
    
    def on_track_added(self, event: Event):
        if event.data.get("category") == "audiobook":
            # React to audiobook additions
            self.process_audiobook(event.data["track"])
    
    def download_item(self, item_id: str, metadata: Dict[str, Any]) -> str:
        # ... download logic
        
        # Emit custom event
        emit_custom_event("MyPlugin", "download_completed", {
            "item_id": item_id,
            "file_path": result_path
        })
        
        return result_path
```

### Repository Integration
```python
# In repository implementation
class IpodRepository(Repository, EventEmittingRepository):
    def __init__(self, device_path: str = None):
        super().__init__("IpodRepository")
        # ... existing init
    
    def add_track(self, track: Track) -> str:
        # ... existing implementation
        
        # Emit event after successful addition
        self._emit_track_event(EventType.TRACK_ADDED, track_id, {
            "title": track.title,
            "category": track.category
        })
        
        return track_id
```

## Success Criteria

When this task is complete, you should have:

1. **Working event system** with sync and async support
2. **Repository integration** that emits events for data changes
3. **Built-in listeners** for logging, statistics, and cache management
4. **Plugin support** for custom events and listeners
5. **Comprehensive tests** covering all event scenarios
6. **Performance optimization** for high-frequency events
7. **Documentation** for event-driven development

## Next Steps

After completing this task:
- Plugins can listen for system events and react accordingly
- UI components can update in real-time based on events
- System monitoring can track all operations through events
- Analytics can be built on top of the event stream

## Resources

- [Observer pattern explanation](https://refactoring.guru/design-patterns/observer)
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Weak references guide](https://docs.python.org/3/library/weakref.html)
- GTKPod signal system for inspiration

## Questions for Code Review

1. Are the pre-defined event types comprehensive enough?
2. Is the weak reference management working correctly?
3. Does the async event handling perform well?
4. Are the convenience functions useful and well-designed?
5. Is the event history and correlation tracking helpful?
6. Will this system scale to high-frequency events?