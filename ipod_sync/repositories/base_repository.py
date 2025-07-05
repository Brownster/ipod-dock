"""Base repository with event integration."""
from abc import ABC
from typing import Any
import uuid

from ..events import event_bus, EventType

class EventEmittingRepository(ABC):
    """Base class for repositories that emit events."""

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    def _emit_track_event(
        self, event_type: EventType, track_id: str, track_data: dict | None = None
    ) -> None:
        """Emit a track-related event."""
        correlation_id = str(uuid.uuid4())
        event_bus.emit(
            event_type,
            self.source_name,
            {"track_id": track_id, "track": track_data or {}},
            correlation_id,
        )

    def _emit_playlist_event(
        self, event_type: EventType, playlist_id: str, playlist_data: dict | None = None
    ) -> None:
        """Emit a playlist-related event."""
        correlation_id = str(uuid.uuid4())
        event_bus.emit(
            event_type,
            self.source_name,
            {"playlist_id": playlist_id, "playlist": playlist_data or {}},
            correlation_id,
        )
