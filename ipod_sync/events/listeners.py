"""Built-in event listeners for common operations."""
import logging
from typing import Dict, Any

from . import Event, EventType, event_bus

logger = logging.getLogger(__name__)

class LoggingListener:
    """Logs all events for debugging."""

    def __init__(self, log_level: int = logging.INFO) -> None:
        self.log_level = log_level

        for event_type in EventType:
            event_bus.on(event_type, self.log_event, weak_ref=False)

    def log_event(self, event: Event) -> None:
        logger.log(
            self.log_level,
            f"Event: {event.type.value} from {event.source} with data: {event.data}",
        )

class StatisticsCollector:
    """Collects statistics about system usage."""

    def __init__(self) -> None:
        self.stats: Dict[str, Any] = {
            "tracks_added": 0,
            "tracks_removed": 0,
            "syncs_completed": 0,
            "syncs_failed": 0,
            "plugins_loaded": 0,
        }

        event_bus.on(EventType.TRACK_ADDED, self.on_track_added, weak_ref=False)
        event_bus.on(EventType.TRACK_REMOVED, self.on_track_removed, weak_ref=False)
        event_bus.on(EventType.SYNC_COMPLETED, self.on_sync_completed, weak_ref=False)
        event_bus.on(EventType.SYNC_FAILED, self.on_sync_failed, weak_ref=False)
        event_bus.on(EventType.PLUGIN_LOADED, self.on_plugin_loaded, weak_ref=False)

    def on_track_added(self, event: Event) -> None:
        self.stats["tracks_added"] += 1

    def on_track_removed(self, event: Event) -> None:
        self.stats["tracks_removed"] += 1

    def on_sync_completed(self, event: Event) -> None:
        self.stats["syncs_completed"] += 1

    def on_sync_failed(self, event: Event) -> None:
        self.stats["syncs_failed"] += 1

    def on_plugin_loaded(self, event: Event) -> None:
        self.stats["plugins_loaded"] += 1

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()

class CacheInvalidator:
    """Invalidates caches when data changes."""

    def __init__(self) -> None:
        event_bus.on(EventType.TRACK_ADDED, self.invalidate_track_cache, weak_ref=False)
        event_bus.on(EventType.TRACK_UPDATED, self.invalidate_track_cache, weak_ref=False)
        event_bus.on(EventType.TRACK_REMOVED, self.invalidate_track_cache, weak_ref=False)
        event_bus.on(EventType.PLAYLIST_CREATED, self.invalidate_playlist_cache, weak_ref=False)
        event_bus.on(EventType.PLAYLIST_UPDATED, self.invalidate_playlist_cache, weak_ref=False)
        event_bus.on(EventType.PLAYLIST_DELETED, self.invalidate_playlist_cache, weak_ref=False)

    def invalidate_track_cache(self, event: Event) -> None:
        logger.debug("Invalidating track cache due to event")
        # Implementation would clear actual caches

    def invalidate_playlist_cache(self, event: Event) -> None:
        logger.debug("Invalidating playlist cache due to event")
        # Implementation would clear actual caches

# Initialize built-in listeners

def initialize_builtin_listeners() -> None:
    """Initialize built-in event listeners."""
    global _logging_listener, _stats_collector, _cache_invalidator

    _logging_listener = LoggingListener(logging.DEBUG)
    _stats_collector = StatisticsCollector()
    _cache_invalidator = CacheInvalidator()

    logger.info("Initialized built-in event listeners")

_logging_listener = None
_stats_collector: StatisticsCollector | None = None
_cache_invalidator = None

def get_statistics_collector() -> StatisticsCollector:
    """Get the global statistics collector."""
    if _stats_collector is None:
        initialize_builtin_listeners()
    return _stats_collector
