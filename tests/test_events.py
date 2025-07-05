"""Tests for event system."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync.events import (
    EventBus,
    Event,
    EventType,
    emit_track_added,
    emit_sync_started,
)

class TestEvent:
    def test_event_creation(self):
        event = Event(
            type=EventType.TRACK_ADDED,
            source="test_component",
            data={"track_id": "123", "title": "Test Track"},
        )

        assert event.type == EventType.TRACK_ADDED
        assert event.source == "test_component"
        assert event.data["track_id"] == "123"
        assert isinstance(event.timestamp, datetime)

class TestEventBus:
    def setup_method(self):
        self.event_bus = EventBus()

    def test_register_sync_listener(self):
        mock_callback = Mock()

        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {"track_id": "123"})

        mock_callback.assert_called_once()
        event = mock_callback.call_args[0][0]
        assert event.type == EventType.TRACK_ADDED
        assert event.data["track_id"] == "123"

    def test_register_async_listener(self):
        mock_callback = AsyncMock()

        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        asyncio.run(self.event_bus.emit_async(EventType.TRACK_ADDED, "test", {"track_id": "123"}))

        mock_callback.assert_called_once()

    def test_unregister_listener(self):
        mock_callback = Mock()
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        success = self.event_bus.off(EventType.TRACK_ADDED, mock_callback)

        assert success is True
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        mock_callback.assert_not_called()

    def test_event_history(self):
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {"track_id": "123"})
        self.event_bus.emit(EventType.SYNC_STARTED, "test", {"queue_size": 5})

        all_events = self.event_bus.get_recent_events()
        assert len(all_events) == 2

        track_events = self.event_bus.get_recent_events(EventType.TRACK_ADDED)
        assert len(track_events) == 1
        assert track_events[0].type == EventType.TRACK_ADDED

    def test_weak_references(self):
        class TestListener:
            def __init__(self):
                self.called = False

            def callback(self, event):
                self.called = True

        listener = TestListener()
        self.event_bus.on(EventType.TRACK_ADDED, listener.callback)
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        assert listener.called is True

        # Delete listener object
        listener_ref = listener
        del listener

        self.event_bus._cleanup_listeners(EventType.TRACK_ADDED)
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        assert listener_ref.called is True

    def test_error_handling(self):
        def failing_callback(event):
            raise Exception("Test exception")

        good_callback = Mock()

        self.event_bus.on(EventType.TRACK_ADDED, failing_callback, weak_ref=False)
        self.event_bus.on(EventType.TRACK_ADDED, good_callback, weak_ref=False)

        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})

        good_callback.assert_called_once()
        stats = self.event_bus.get_stats()
        assert stats["errors"] > 0

    def test_correlation_id(self):
        correlation_id = "test-correlation-123"

        self.event_bus.emit(EventType.SYNC_STARTED, "test", {}, correlation_id)
        self.event_bus.emit(EventType.SYNC_COMPLETED, "test", {}, correlation_id)

        related_events = self.event_bus.get_recent_events(correlation_id=correlation_id)
        assert len(related_events) == 2
        assert all(e.correlation_id == correlation_id for e in related_events)

class TestConvenienceFunctions:
    def test_emit_track_added(self):
        from ipod_sync.events import event_bus
        event_bus.clear_history()

        emit_track_added("test_source", "track123", {"title": "Test Track"})

        events = event_bus.get_recent_events(EventType.TRACK_ADDED)
        assert len(events) == 1
        assert events[0].data["track_id"] == "track123"
        assert events[0].data["track"]["title"] == "Test Track"

    def test_emit_sync_started(self):
        from ipod_sync.events import event_bus
        event_bus.clear_history()

        emit_sync_started("sync_service", 5)

        events = event_bus.get_recent_events(EventType.SYNC_STARTED)
        assert len(events) == 1
        assert events[0].data["queue_size"] == 5
        assert "started_at" in events[0].data

class TestEventType:
    def test_event_type_values(self):
        assert EventType.TRACK_ADDED.value == "track_added"
        assert EventType.TRACK_UPDATED.value == "track_updated"
        assert EventType.TRACK_REMOVED.value == "track_removed"
        assert EventType.PLAYLIST_CREATED.value == "playlist_created"
        assert EventType.SYNC_STARTED.value == "sync_started"
        assert EventType.SYNC_COMPLETED.value == "sync_completed"
        assert EventType.PLUGIN_LOADED.value == "plugin_loaded"
        assert EventType.IPOD_CONNECTED.value == "ipod_connected"

