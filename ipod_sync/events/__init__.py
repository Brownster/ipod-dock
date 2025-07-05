"""Event system for loose coupling between components."""
import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
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

    def __post_init__(self) -> None:
        """Ensure timestamp is set."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventListener:
    """Wrapper for event listener callbacks."""

    def __init__(self, callback: Callable, is_async: bool = False, weak_ref: bool = True) -> None:
        self.is_async = is_async
        self.weak_ref = weak_ref

        if weak_ref and hasattr(callback, "__self__"):
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
        return self._callback_ref()

    def is_valid(self) -> bool:
        """Check if the callback is still valid."""
        return self.get_callback() is not None

class EventBus:
    """Central event bus for application-wide event handling."""

    def __init__(self, max_history: int = 1000) -> None:
        self._listeners: Dict[EventType, List[EventListener]] = {}
        self._event_history: List[Event] = []
        self._max_history = max_history
        self._stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "listeners_called": 0,
            "errors": 0,
        }

    def on(self, event_type: EventType, callback: Callable[[Event], Any], weak_ref: bool = True) -> None:
        """Register a listener (sync or async)."""
        if not callable(callback):
            raise ValueError("Callback must be callable")

        is_async = inspect.iscoroutinefunction(callback)
        listener = EventListener(callback, is_async=is_async, weak_ref=weak_ref)

        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append(listener)
        logger.debug(
            "Registered %s listener for %s",
            "async" if is_async else "sync",
            event_type.value,
        )

    def off(self, event_type: EventType, callback: Callable) -> bool:
        """Unregister an event listener."""
        if event_type not in self._listeners:
            return False

        listeners = self._listeners[event_type]
        for i, listener in enumerate(listeners):
            listener_callback = listener.get_callback()
            if listener_callback == callback:
                listeners.pop(i)
                logger.debug("Unregistered listener for %s", event_type.value)
                return True

        return False

    def emit(
        self,
        event_type: EventType,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Emit an event synchronously."""
        event = Event(type=event_type, source=source, data=data or {}, correlation_id=correlation_id)

        self._store_event(event)
        self._stats["events_emitted"] += 1

        # Clean up dead listeners first
        self._cleanup_listeners(event_type)

        listeners = self._listeners.get(event_type, [])
        for listener in listeners:
            try:
                callback = listener.get_callback()
                if callback:
                    if listener.is_async:
                        try:
                            loop = asyncio.get_event_loop()
                            loop.create_task(callback(event))
                        except RuntimeError:
                            logger.warning(
                                "Skipping async callback for %s - no event loop",
                                event_type.value,
                            )
                    else:
                        callback(event)
                    self._stats["listeners_called"] += 1
            except Exception as e:  # pragma: no cover - logging
                self._stats["errors"] += 1
                logger.error(
                    "Error in event listener for %s: %s", event_type.value, e, exc_info=True
                )

        self._stats["events_processed"] += 1
        logger.debug("Emitted event %s from %s", event_type.value, source)

    async def emit_async(
        self,
        event_type: EventType,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Emit an event asynchronously."""
        event = Event(type=event_type, source=source, data=data or {}, correlation_id=correlation_id)

        self._store_event(event)
        self._stats["events_emitted"] += 1

        self._cleanup_listeners(event_type)

        sync_callbacks: List[Callable] = []
        async_callbacks: List[Callable] = []

        listeners = self._listeners.get(event_type, [])
        for listener in listeners:
            callback = listener.get_callback()
            if callback:
                if listener.is_async:
                    async_callbacks.append(callback)
                else:
                    sync_callbacks.append(callback)

        for callback in sync_callbacks:
            try:
                callback(event)
                self._stats["listeners_called"] += 1
            except Exception as e:  # pragma: no cover - logging
                self._stats["errors"] += 1
                logger.error(
                    "Error in sync event listener for %s: %s", event_type.value, e
                )

        if async_callbacks:
            tasks = []
            for callback in async_callbacks:
                try:
                    tasks.append(asyncio.create_task(callback(event)))
                except Exception as e:  # pragma: no cover - logging
                    self._stats["errors"] += 1
                    logger.error(
                        "Error creating async task for %s: %s", event_type.value, e
                    )

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        self._stats["errors"] += 1
                        logger.error(
                            "Error in async event listener for %s: %s",
                            event_type.value,
                            result,
                        )
                    else:
                        self._stats["listeners_called"] += 1

        self._stats["events_processed"] += 1
        logger.debug("Emitted async event %s from %s", event_type.value, source)

    def _cleanup_listeners(self, event_type: EventType) -> None:
        """Remove dead weak references."""
        if event_type not in self._listeners:
            return

        valid_listeners = [l for l in self._listeners[event_type] if l.is_valid()]
        self._listeners[event_type] = valid_listeners

    def _store_event(self, event: Event) -> None:
        """Store event in history."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history :]

    def get_recent_events(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[Event]:
        """Get recent events with optional filtering."""
        events = self._event_history
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
            "active_listeners": sum(len(l) for l in self._listeners.values()),
            "event_types": list(self._listeners.keys()),
            "history_size": len(self._event_history),
        }

    def get_listener_count(self, event_type: EventType) -> int:
        """Get number of listeners for an event type."""
        self._cleanup_listeners(event_type)
        return len(self._listeners.get(event_type, []))

# Global event bus instance
event_bus = EventBus()

# Convenience functions for common events

def emit_track_added(
    source: str,
    track_id: str,
    track_data: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> None:
    """Emit track added event."""
    event_bus.emit(
        EventType.TRACK_ADDED,
        source,
        {"track_id": track_id, "track": track_data},
        correlation_id,
    )


def emit_sync_started(
    source: str, queue_size: int, correlation_id: Optional[str] = None
) -> None:
    """Emit sync started event."""
    event_bus.emit(
        EventType.SYNC_STARTED,
        source,
        {"queue_size": queue_size, "started_at": datetime.now().isoformat()},
        correlation_id,
    )


def emit_sync_progress(
    source: str,
    completed: int,
    total: int,
    correlation_id: Optional[str] = None,
) -> None:
    """Emit sync progress event."""
    percentage = (completed / total * 100) if total > 0 else 0
    event_bus.emit(
        EventType.SYNC_PROGRESS,
        source,
        {"completed": completed, "total": total, "percentage": percentage},
        correlation_id,
    )


def emit_sync_completed(
    source: str,
    synced_count: int,
    duration: float,
    correlation_id: Optional[str] = None,
) -> None:
    """Emit sync completed event."""
    event_bus.emit(
        EventType.SYNC_COMPLETED,
        source,
        {
            "synced_count": synced_count,
            "duration_seconds": duration,
            "completed_at": datetime.now().isoformat(),
        },
        correlation_id,
    )


async def emit_plugin_loaded(
    source: str,
    plugin_id: str,
    plugin_name: str,
    correlation_id: Optional[str] = None,
) -> None:
    """Emit plugin loaded event."""
    await event_bus.emit_async(
        EventType.PLUGIN_LOADED,
        source,
        {"plugin_id": plugin_id, "plugin_name": plugin_name},
        correlation_id,
    )


def emit_ipod_connected(
    source: str, device_path: str, correlation_id: Optional[str] = None
) -> None:
    """Emit iPod connected event."""
    event_bus.emit(
        EventType.IPOD_CONNECTED,
        source,
        {"device_path": device_path, "connected_at": datetime.now().isoformat()},
        correlation_id,
    )


def emit_custom_event(
    source: str, event_name: str, data: Dict[str, Any], correlation_id: Optional[str] = None
) -> None:
    """Emit a custom event (for plugins)."""
    event_bus.emit(
        EventType.CUSTOM,
        source,
        {"event_name": event_name, **data},
        correlation_id,
    )
