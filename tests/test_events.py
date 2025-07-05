"""Tests for event system."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from ipod_sync.events import EventBus, Event, EventType, emit_track_added, emit_sync_started

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
    
    def test_event_auto_timestamp(self):
        """Test Event automatically sets timestamp."""
        event = Event(
            type=EventType.SYNC_STARTED,
            source="sync_service",
            data={}
        )
        
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

class TestEventBus:
    def setup_method(self):
        """Set up test environment."""
        self.event_bus = EventBus()
    
    def test_register_sync_listener(self):
        """Test registering synchronous event listener."""
        mock_callback = Mock()
        
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        
        assert EventType.TRACK_ADDED in self.event_bus._listeners
        assert mock_callback in self.event_bus._listeners[EventType.TRACK_ADDED]
    
    def test_register_async_listener(self):
        """Test registering asynchronous event listener."""
        mock_callback = AsyncMock()
        
        self.event_bus.on_async(EventType.TRACK_ADDED, mock_callback)
        
        assert EventType.TRACK_ADDED in self.event_bus._async_listeners
        assert mock_callback in self.event_bus._async_listeners[EventType.TRACK_ADDED]
    
    def test_unregister_listener(self):
        """Test unregistering event listener."""
        mock_callback = Mock()
        
        # Register and then unregister
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        self.event_bus.off(EventType.TRACK_ADDED, mock_callback)
        
        # Should be removed
        listeners = self.event_bus._listeners.get(EventType.TRACK_ADDED, [])
        assert mock_callback not in listeners
    
    def test_emit_sync_event(self):
        """Test emitting synchronous event."""
        mock_callback = Mock()
        self.event_bus.on(EventType.TRACK_ADDED, mock_callback)
        
        test_data = {"track_id": "123", "title": "Test"}
        self.event_bus.emit(EventType.TRACK_ADDED, "test_source", test_data)
        
        # Verify callback was called
        mock_callback.assert_called_once()
        event = mock_callback.call_args[0][0]
        assert event.type == EventType.TRACK_ADDED
        assert event.source == "test_source"
        assert event.data == test_data
    
    @pytest.mark.asyncio
    async def test_emit_async_event(self):
        """Test emitting asynchronous event."""
        mock_sync_callback = Mock()
        mock_async_callback = AsyncMock()
        
        self.event_bus.on(EventType.TRACK_ADDED, mock_sync_callback)
        self.event_bus.on_async(EventType.TRACK_ADDED, mock_async_callback)
        
        test_data = {"track_id": "123"}
        await self.event_bus.emit_async(EventType.TRACK_ADDED, "test_source", test_data)
        
        # Both callbacks should be called
        mock_sync_callback.assert_called_once()
        mock_async_callback.assert_called_once()
    
    def test_event_history_storage(self):
        """Test event history is stored."""
        self.event_bus.emit(EventType.TRACK_ADDED, "test_source", {"test": "data"})
        
        history = self.event_bus.get_recent_events()
        assert len(history) == 1
        assert history[0].type == EventType.TRACK_ADDED
        assert history[0].source == "test_source"
    
    def test_event_history_filtering(self):
        """Test filtering event history by type."""
        # Emit different types of events
        self.event_bus.emit(EventType.TRACK_ADDED, "source1", {})
        self.event_bus.emit(EventType.SYNC_STARTED, "source2", {})
        self.event_bus.emit(EventType.TRACK_ADDED, "source3", {})
        
        # Filter by event type
        track_events = self.event_bus.get_recent_events(EventType.TRACK_ADDED)
        sync_events = self.event_bus.get_recent_events(EventType.SYNC_STARTED)
        
        assert len(track_events) == 2
        assert len(sync_events) == 1
        assert all(e.type == EventType.TRACK_ADDED for e in track_events)
        assert sync_events[0].type == EventType.SYNC_STARTED
    
    def test_event_history_limit(self):
        """Test event history respects limit parameter."""
        # Emit multiple events
        for i in range(10):
            self.event_bus.emit(EventType.TRACK_ADDED, f"source{i}", {"index": i})
        
        # Get limited history
        recent_events = self.event_bus.get_recent_events(limit=5)
        assert len(recent_events) == 5
        
        # Should be the most recent ones
        assert recent_events[-1].data["index"] == 9
        assert recent_events[0].data["index"] == 5
    
    def test_clear_history(self):
        """Test clearing event history."""
        # Add some events
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        self.event_bus.emit(EventType.SYNC_STARTED, "test", {})
        
        assert len(self.event_bus.get_recent_events()) == 2
        
        # Clear history
        self.event_bus.clear_history()
        
        assert len(self.event_bus.get_recent_events()) == 0
    
    def test_exception_in_listener(self):
        """Test event bus handles exceptions in listeners gracefully."""
        def failing_callback(event):
            raise Exception("Test exception")
        
        good_callback = Mock()
        
        self.event_bus.on(EventType.TRACK_ADDED, failing_callback)
        self.event_bus.on(EventType.TRACK_ADDED, good_callback)
        
        # Should not raise exception
        self.event_bus.emit(EventType.TRACK_ADDED, "test", {})
        
        # Good callback should still be called
        good_callback.assert_called_once()
    
    def test_history_size_limit(self):
        """Test event history respects maximum size."""
        # Set small history limit for testing
        self.event_bus._max_history = 5
        
        # Emit more events than the limit
        for i in range(10):
            self.event_bus.emit(EventType.TRACK_ADDED, "test", {"index": i})
        
        history = self.event_bus.get_recent_events()
        
        # Should only keep the most recent events
        assert len(history) == 5
        assert history[0].data["index"] == 5  # First event in history
        assert history[-1].data["index"] == 9  # Last event in history

class TestConvenienceFunctions:
    def test_emit_track_added(self):
        """Test emit_track_added convenience function."""
        from ipod_sync.events import event_bus
        
        # Clear any existing history
        event_bus.clear_history()
        
        emit_track_added("test_source", "track123", {"title": "Test Track"})
        
        events = event_bus.get_recent_events(EventType.TRACK_ADDED)
        assert len(events) == 1
        assert events[0].data["track_id"] == "track123"
        assert events[0].data["track"]["title"] == "Test Track"
    
    def test_emit_sync_started(self):
        """Test emit_sync_started convenience function."""
        from ipod_sync.events import event_bus
        
        # Clear any existing history
        event_bus.clear_history()
        
        emit_sync_started("sync_service", 5)
        
        events = event_bus.get_recent_events(EventType.SYNC_STARTED)
        assert len(events) == 1
        assert events[0].data["queue_size"] == 5
        assert "started_at" in events[0].data

class TestEventType:
    def test_event_type_values(self):
        """Test EventType enum values."""
        assert EventType.TRACK_ADDED.value == "track_added"
        assert EventType.TRACK_UPDATED.value == "track_updated"
        assert EventType.TRACK_REMOVED.value == "track_removed"
        assert EventType.PLAYLIST_CREATED.value == "playlist_created"
        assert EventType.SYNC_STARTED.value == "sync_started"
        assert EventType.SYNC_COMPLETED.value == "sync_completed"
        assert EventType.PLUGIN_LOADED.value == "plugin_loaded"
        assert EventType.IPOD_CONNECTED.value == "ipod_connected"