# Task 2: Implement Repository Pattern for Data Access

**Priority**: High  
**Estimated Time**: 2-3 days  
**Skills Required**: Python design patterns, data abstraction  
**Assigned to**: _[Developer Name]_  
**Depends on**: Can be done in parallel with Task 1

## Overview
Create a repository pattern to abstract data access for different sources (iPod, local files, queue), making the codebase more maintainable and testable. This removes direct database/file system calls from business logic.

## Learning Objectives
- Understand the Repository design pattern
- Learn data access abstraction techniques
- Practice working with libgpod library
- Implement file system operations safely
- Create testable data layer

## Acceptance Criteria
- [ ] Repository base class and interfaces defined
- [ ] iPod, Queue, and Local repositories implemented
- [ ] Existing data access code refactored to use repositories
- [ ] Unit tests for all repositories with >80% coverage
- [ ] Repository factory for easy instantiation
- [ ] Error handling for all data operations

## Background Context
GTKPod uses a sophisticated repository pattern to handle different data sources (local files, iPod database, remote sources). This allows the UI and business logic to work with a consistent interface regardless of where the data comes from.

## Implementation Steps

### Step 2.1: Create Repository Base Classes (0.5 days)

**File**: `ipod_sync/repositories/__init__.py`

```python
"""Repository pattern for data access abstraction."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class TrackStatus(Enum):
    ACTIVE = "active"
    DELETED = "deleted"
    PENDING = "pending"

@dataclass
class Track:
    """Unified track representation across all repositories."""
    id: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    duration: Optional[int] = None  # seconds
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    play_count: int = 0
    rating: int = 0  # 0-5 stars
    status: TrackStatus = TrackStatus.ACTIVE
    category: str = "music"  # music, audiobook, podcast
    metadata: Optional[Dict[str, Any]] = None

@dataclass 
class Playlist:
    """Playlist representation."""
    id: str
    name: str
    track_ids: List[str]
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    is_smart: bool = False
    smart_criteria: Optional[Dict[str, Any]] = None

class Repository(ABC):
    """Base repository interface for data access."""
    
    @abstractmethod
    def get_tracks(self, limit: Optional[int] = None, offset: int = 0) -> List[Track]:
        """Get all tracks with optional pagination."""
        pass
    
    @abstractmethod
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get a specific track by ID."""
        pass
    
    @abstractmethod
    def add_track(self, track: Track) -> str:
        """Add a track and return its ID."""
        pass
    
    @abstractmethod
    def update_track(self, track: Track) -> bool:
        """Update an existing track."""
        pass
    
    @abstractmethod
    def remove_track(self, track_id: str) -> bool:
        """Remove a track by ID."""
        pass
    
    @abstractmethod
    def search_tracks(self, query: str, fields: List[str] = None) -> List[Track]:
        """Search tracks by query in specified fields."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        pass

class PlaylistRepository(ABC):
    """Base playlist repository interface."""
    
    @abstractmethod
    def get_playlists(self) -> List[Playlist]:
        """Get all playlists."""
        pass
    
    @abstractmethod
    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Get a specific playlist by ID."""
        pass
    
    @abstractmethod
    def create_playlist(self, name: str, track_ids: List[str] = None) -> str:
        """Create a new playlist and return its ID."""
        pass
    
    @abstractmethod
    def update_playlist(self, playlist: Playlist) -> bool:
        """Update an existing playlist."""
        pass
    
    @abstractmethod
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist by ID."""
        pass
    
    @abstractmethod
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Add tracks to a playlist."""
        pass
    
    @abstractmethod
    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Remove tracks from a playlist."""
        pass
```

**What to implement:**
1. **Study existing data structures**: Look at how tracks are currently represented
2. **Design unified models**: Create Track and Playlist classes that work for all sources
3. **Define clear interfaces**: Abstract methods should cover all needed operations
4. **Add proper typing**: Use type hints throughout for better IDE support
5. **Consider future needs**: Design interfaces that can accommodate new features

**Key concepts:**
- **Repository Pattern**: Encapsulates data access logic
- **Abstract Base Classes**: Define contracts for implementations
- **Data Transfer Objects**: Track and Playlist as data containers
- **Separation of Concerns**: Business logic vs data access

### Step 2.2: Implement iPod Repository (1 day)

**File**: `ipod_sync/repositories/ipod_repository.py`

Study the existing `api_helpers.py` and `libpod_wrapper.py` first:

```python
"""iPod repository implementation using libgpod."""
import gpod
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from . import Repository, PlaylistRepository, Track, Playlist, TrackStatus
from .. import config

logger = logging.getLogger(__name__)

class IpodRepository(Repository, PlaylistRepository):
    """Repository for iPod data using libgpod."""
    
    def __init__(self, device_path: str = None):
        self.device_path = device_path or config.IPOD_DEVICE
        self._itdb = None
    
    def _ensure_connected(self):
        """Ensure iPod database is loaded."""
        if self._itdb is None:
            mount_point = str(config.IPOD_MOUNT)
            try:
                self._itdb = gpod.Database(mount_point)
                logger.info(f"Connected to iPod at {mount_point}")
            except Exception as e:
                raise RuntimeError(f"Failed to connect to iPod: {e}")
    
    def _gpod_track_to_track(self, gpod_track) -> Track:
        """Convert gpod track to our Track object."""
        return Track(
            id=str(gpod_track.dbid),
            title=gpod_track.title or "Unknown",
            artist=gpod_track.artist,
            album=gpod_track.album,
            genre=gpod_track.genre,
            track_number=gpod_track.track_nr or None,
            duration=gpod_track.tracklen // 1000 if gpod_track.tracklen else None,
            file_path=gpod_track.ipod_path(),
            file_size=gpod_track.size or None,
            bitrate=gpod_track.bitrate or None,
            date_added=datetime.fromtimestamp(gpod_track.time_added) if gpod_track.time_added else None,
            date_modified=datetime.fromtimestamp(gpod_track.time_modified) if gpod_track.time_modified else None,
            play_count=gpod_track.playcount or 0,
            rating=gpod_track.rating // 20 if gpod_track.rating else 0,  # Convert 0-100 to 0-5
            status=TrackStatus.ACTIVE,
            category=self._determine_category(gpod_track),
            metadata={
                "dbid": gpod_track.dbid,
                "compilation": gpod_track.compilation,
                "year": gpod_track.year,
                "bpm": gpod_track.bpm,
                "cd_nr": gpod_track.cd_nr,
                "cds": gpod_track.cds
            }
        )
    
    # ... implement all abstract methods
```

**What to implement:**
1. **Study libgpod**: Understand how the current wrapper works
2. **Connection management**: Handle iPod mount/unmount gracefully
3. **Data conversion**: Transform between gpod objects and our Track/Playlist models
4. **Error handling**: Wrap all libgpod calls with proper exception handling
5. **Performance**: Consider caching strategies for large libraries

**Key libgpod concepts:**
- **Database object**: Represents the entire iPod database
- **Track objects**: Individual songs with metadata
- **Playlist objects**: Collections of tracks
- **File paths**: iPod uses special path format

**Testing strategy:**
- Mock libgpod for unit tests
- Use test fixtures for integration tests
- Test error conditions (disconnected iPod, corrupted database)

### Step 2.3: Implement Queue Repository (1 day)

**File**: `ipod_sync/repositories/queue_repository.py`

Study the existing queue management in `api_helpers.py`:

```python
"""Queue repository for managing sync queue files."""
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import mimetypes
import mutagen

from . import Repository, Track, TrackStatus
from .. import config

class QueueRepository(Repository):
    """Repository for sync queue files."""
    
    def __init__(self, queue_dir: Path = None):
        self.queue_dir = queue_dir or config.SYNC_QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata file to track queue items
        self.metadata_file = self.queue_dir / ".queue_metadata.json"
        if not self.metadata_file.exists():
            self._save_metadata({})
    
    def _extract_metadata_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from audio file using mutagen."""
        try:
            audio_file = mutagen.File(str(file_path))
            if not audio_file:
                return {}
            
            metadata = {}
            
            # Common fields across formats
            title = audio_file.get('TIT2') or audio_file.get('\xa9nam') or audio_file.get('TITLE')
            if title:
                metadata['title'] = str(title[0]) if isinstance(title, list) else str(title)
            
            # ... extract other metadata fields
            
            return metadata
            
        except Exception:
            return {}
    
    # ... implement all abstract methods
```

**What to implement:**
1. **File system operations**: Safe file handling with proper error checking
2. **Metadata extraction**: Use mutagen to read audio file metadata
3. **Category detection**: Determine music/audiobook/podcast from file properties
4. **Search functionality**: Implement text search across metadata
5. **Performance**: Handle large numbers of files efficiently

**Key concepts:**
- **Mutagen library**: Cross-format audio metadata extraction
- **File watching**: Detect when new files are added
- **Metadata caching**: Store extracted metadata to avoid re-processing
- **Category inference**: Smart categorization of content

### Step 2.4: Create Repository Factory (0.5 days)

**File**: `ipod_sync/repositories/factory.py`

```python
"""Repository factory for creating repository instances."""
from typing import Dict, Any, Optional
from pathlib import Path

from . import Repository, PlaylistRepository
from .ipod_repository import IpodRepository
from .queue_repository import QueueRepository
from .. import config

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    @staticmethod
    def create_ipod_repository(device_path: str = None) -> IpodRepository:
        """Create an iPod repository."""
        return IpodRepository(device_path or config.IPOD_DEVICE)
    
    @staticmethod
    def create_queue_repository(queue_dir: Path = None) -> QueueRepository:
        """Create a queue repository."""
        return QueueRepository(queue_dir or config.SYNC_QUEUE_DIR)
    
    @staticmethod
    def get_repository(repo_type: str, **kwargs) -> Repository:
        """Get a repository by type."""
        if repo_type == "ipod":
            return RepositoryFactory.create_ipod_repository(kwargs.get('device_path'))
        elif repo_type == "queue":
            return RepositoryFactory.create_queue_repository(kwargs.get('queue_dir'))
        else:
            raise ValueError(f"Unknown repository type: {repo_type}")

# Convenience functions
def get_ipod_repo(device_path: str = None) -> IpodRepository:
    """Get iPod repository instance."""
    return RepositoryFactory.create_ipod_repository(device_path)

def get_queue_repo(queue_dir: Path = None) -> QueueRepository:
    """Get queue repository instance.""" 
    return RepositoryFactory.create_queue_repository(queue_dir)
```

**What to implement:**
1. **Factory pattern**: Centralized repository creation
2. **Configuration integration**: Use app config for default parameters
3. **Type safety**: Proper return type annotations
4. **Convenience functions**: Easy-to-use helper functions
5. **Extensibility**: Easy to add new repository types

## Testing Requirements

**File**: `tests/test_repositories.py`

Create comprehensive tests covering:

```python
"""Tests for repository pattern implementation."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from ipod_sync.repositories import Track, Playlist, TrackStatus, Repository
from ipod_sync.repositories.queue_repository import QueueRepository
from ipod_sync.repositories.factory import RepositoryFactory

class TestTrack:
    def test_track_creation(self):
        track = Track(
            id="test123",
            title="Test Track",
            artist="Test Artist",
            album="Test Album"
        )
        
        assert track.id == "test123"
        assert track.title == "Test Track"
        assert track.status == TrackStatus.ACTIVE

class TestQueueRepository:
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = QueueRepository(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_add_track(self):
        """Test adding a track to queue."""
        track = Track(
            id="test_track",
            title="Test Track",
            artist="Test Artist",
            category="music"
        )
        
        track_id = self.repo.add_track(track)
        assert track_id is not None
        
        # Verify track can be retrieved
        retrieved_track = self.repo.get_track(track_id)
        assert retrieved_track is not None
        assert retrieved_track.title == "Test Track"
    
    # ... more tests
```

**Test coverage requirements:**
- [ ] Track and Playlist data classes
- [ ] Repository interfaces and abstract methods
- [ ] Queue repository file operations
- [ ] iPod repository libgpod integration (mocked)
- [ ] Factory pattern functionality
- [ ] Error handling scenarios

## Integration with Existing Code

### Files to Update

**`ipod_sync/api_helpers.py`**
```python
# Before: Direct libgpod calls
def get_tracks(device_path):
    itdb = gpod.Database("/mnt/ipod")
    # ... direct database access

# After: Use repository
from .repositories.factory import get_ipod_repo

def get_tracks(device_path):
    repo = get_ipod_repo(device_path)
    return repo.get_tracks()
```

**`ipod_sync/app.py`**
```python
# Update endpoints to use repositories
from .repositories.factory import get_ipod_repo, get_queue_repo

@app.get("/tracks")
async def tracks():
    repo = get_ipod_repo()
    tracks = repo.get_tracks()
    return [track_to_dict(track) for track in tracks]
```

## Troubleshooting Guide

### Common Issues

**libgpod connection errors:**
- Check iPod is properly mounted
- Verify mount point permissions
- Test with `gpod.Database()` directly

**File metadata extraction fails:**
- Install mutagen: `pip install mutagen`
- Check supported file formats
- Handle corrupted files gracefully

**Performance issues with large libraries:**
- Implement pagination in get_tracks()
- Add caching for frequently accessed data
- Use database indexes for searching

### Testing Tips

**Mock libgpod for testing:**
```python
@patch('gpod.Database')
def test_ipod_repository(self, mock_db):
    mock_track = Mock()
    mock_track.title = "Test"
    mock_db.return_value.__iter__.return_value = [mock_track]
    
    repo = IpodRepository()
    tracks = repo.get_tracks()
    assert len(tracks) == 1
```

**Use temporary directories for file tests:**
```python
import tempfile
import shutil

def setup_method(self):
    self.temp_dir = Path(tempfile.mkdtemp())

def teardown_method(self):
    shutil.rmtree(self.temp_dir)
```

## Success Criteria

When this task is complete, you should have:

1. **Clean data access layer** that abstracts implementation details
2. **Consistent interfaces** for all data operations
3. **Comprehensive tests** covering all repository implementations
4. **Improved maintainability** through separation of concerns
5. **Foundation for future features** like caching, offline mode, etc.

## Next Steps

After completing this task:
- Task 3 can use repositories in API endpoints
- Task 1 plugins can use repositories as data sources
- Task 5 events can be triggered by repository operations

## Resources

- [Repository Pattern explanation](https://martinfowler.com/eaaCatalog/repository.html)
- [Python ABC documentation](https://docs.python.org/3/library/abc.html)
- [Mutagen library docs](https://mutagen.readthedocs.io/)
- Existing `api_helpers.py` for current data access patterns
- GTKPod repository implementations for inspiration

## Questions for Code Review

1. Do the repository interfaces cover all necessary operations?
2. Is the Track/Playlist data model comprehensive enough?
3. Are error conditions handled appropriately?
4. Is the factory pattern implemented correctly?
5. Are the tests realistic and comprehensive?
6. Will this design scale to large music libraries?