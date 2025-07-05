"""Queue repository for managing sync queue files."""
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import mimetypes
import mutagen

from . import Repository, Track, TrackStatus
from .base_repository import EventEmittingRepository
from ..events import EventType
from .. import config

class QueueRepository(Repository, EventEmittingRepository):
    """Repository for sync queue files."""
    
    def __init__(self, queue_dir: Path = None):
        EventEmittingRepository.__init__(self, "QueueRepository")
        self.queue_dir = queue_dir or config.SYNC_QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata file to track queue items
        self.metadata_file = self.queue_dir / ".queue_metadata.json"
        if not self.metadata_file.exists():
            self._save_metadata({})
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load queue metadata."""
        try:
            return json.loads(self.metadata_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save queue metadata."""
        self.metadata_file.write_text(json.dumps(metadata, indent=2, default=str))
    
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
            
            artist = audio_file.get('TPE1') or audio_file.get('\xa9ART') or audio_file.get('ARTIST')
            if artist:
                metadata['artist'] = str(artist[0]) if isinstance(artist, list) else str(artist)
            
            album = audio_file.get('TALB') or audio_file.get('\xa9alb') or audio_file.get('ALBUM')
            if album:
                metadata['album'] = str(album[0]) if isinstance(album, list) else str(album)
            
            genre = audio_file.get('TCON') or audio_file.get('\xa9gen') or audio_file.get('GENRE')
            if genre:
                metadata['genre'] = str(genre[0]) if isinstance(genre, list) else str(genre)
            
            track_num = audio_file.get('TRCK') or audio_file.get('trkn') or audio_file.get('TRACKNUMBER')
            if track_num:
                track_str = str(track_num[0]) if isinstance(track_num, list) else str(track_num)
                try:
                    # Handle "1/12" format
                    metadata['track_number'] = int(track_str.split('/')[0])
                except (ValueError, IndexError):
                    pass
            
            # Duration
            if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                metadata['duration'] = int(audio_file.info.length)
            
            # Bitrate
            if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'bitrate'):
                metadata['bitrate'] = audio_file.info.bitrate
            
            return metadata
            
        except Exception:
            return {}
    
    def _determine_category_from_path(self, file_path: Path) -> str:
        """Determine category based on file path."""
        # Check if file is in a category subdirectory
        if file_path.parent.name in ['music', 'audiobook', 'podcast']:
            return file_path.parent.name
        
        # Check by file extension or metadata
        try:
            audio_file = mutagen.File(str(file_path))
        except Exception:
            audio_file = None
        if audio_file:
            # Check for audiobook indicators
            genre = audio_file.get('TCON') or audio_file.get('\xa9gen') or audio_file.get('GENRE')
            if genre:
                genre_str = str(genre[0] if isinstance(genre, list) else genre).lower()
                if 'audiobook' in genre_str or 'spoken' in genre_str:
                    return 'audiobook'
                if 'podcast' in genre_str:
                    return 'podcast'
        
        # Default to music
        return 'music'
    
    def get_tracks(self, limit: Optional[int] = None, offset: int = 0) -> List[Track]:
        """Get all tracks in queue."""
        tracks = []
        metadata = self._load_metadata()
        
        # Find all audio files in queue directory
        audio_extensions = {'.mp3', '.m4a', '.m4b', '.aac', '.flac', '.wav', '.ogg'}
        
        for file_path in self.queue_dir.rglob('*'):
            if file_path.suffix.lower() not in audio_extensions:
                continue
            if file_path.name.startswith('.'):
                continue
            
            file_id = str(file_path.relative_to(self.queue_dir))
            file_metadata = metadata.get(file_id, {})
            
            # Extract metadata if not cached
            if not file_metadata:
                file_metadata = self._extract_metadata_from_file(file_path)
                file_metadata['date_added'] = datetime.now().isoformat()
                file_metadata['category'] = self._determine_category_from_path(file_path)
                metadata[file_id] = file_metadata
                self._save_metadata(metadata)
            
            stat = file_path.stat()
            
            track = Track(
                id=file_id,
                title=file_metadata.get('title', file_path.stem),
                artist=file_metadata.get('artist'),
                album=file_metadata.get('album'),
                genre=file_metadata.get('genre'),
                track_number=file_metadata.get('track_number'),
                duration=file_metadata.get('duration'),
                file_path=str(file_path),
                file_size=stat.st_size,
                bitrate=file_metadata.get('bitrate'),
                date_added=datetime.fromisoformat(file_metadata.get('date_added', datetime.now().isoformat())),
                date_modified=datetime.fromtimestamp(stat.st_mtime),
                status=TrackStatus.PENDING,
                category=file_metadata.get('category', 'music'),
                metadata=file_metadata
            )
            tracks.append(track)
        
        # Sort by date added (newest first)
        tracks.sort(key=lambda t: t.date_added or datetime.min, reverse=True)
        
        # Apply offset and limit
        if offset > 0:
            tracks = tracks[offset:]
        if limit:
            tracks = tracks[:limit]
        
        return tracks
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get a specific track by ID (relative path)."""
        file_path = self.queue_dir / track_id
        if not file_path.exists():
            return None
        
        tracks = self.get_tracks()
        for track in tracks:
            if track.id == track_id:
                return track
        return None
    
    def add_track(self, track: Track) -> str:
        """Add a track to queue (copy file if needed)."""
        # Generate unique filename if needed
        if not track.file_path:
            filename = f"{track.title or 'unknown'}_{uuid.uuid4().hex[:8]}.mp3"
        else:
            source_path = Path(track.file_path)
            filename = source_path.name
        
        # Determine category subdirectory
        category_dir = self.queue_dir / track.category
        category_dir.mkdir(exist_ok=True)
        
        dest_path = category_dir / filename
        
        # Copy file if source exists and is different
        if track.file_path and Path(track.file_path).exists():
            source_path = Path(track.file_path)
            if source_path != dest_path:
                import shutil
                shutil.copy2(source_path, dest_path)
                # If the source file resides inside the queue directory,
                # remove it to avoid duplicate entries in get_tracks()
                if source_path.parent == self.queue_dir:
                    source_path.unlink(missing_ok=True)
        
        # Update metadata
        metadata = self._load_metadata()
        file_id = str(dest_path.relative_to(self.queue_dir))
        
        metadata[file_id] = {
            'title': track.title,
            'artist': track.artist,
            'album': track.album,
            'genre': track.genre,
            'track_number': track.track_number,
            'duration': track.duration,
            'bitrate': track.bitrate,
            'category': track.category,
            'date_added': (track.date_added or datetime.now()).isoformat(),
            **((track.metadata or {}))
        }
        self._save_metadata(metadata)

        # Emit event
        self._emit_track_event(
            EventType.QUEUE_UPDATED,
            file_id,
            {
                "title": track.title,
                "category": track.category,
                "action": "added",
            },
        )

        return file_id
    
    def update_track(self, track: Track) -> bool:
        """Update track metadata."""
        metadata = self._load_metadata()
        if track.id not in metadata:
            return False
        
        metadata[track.id].update({
            'title': track.title,
            'artist': track.artist,
            'album': track.album,
            'genre': track.genre,
            'track_number': track.track_number,
            'duration': track.duration,
            'bitrate': track.bitrate,
            'category': track.category
        })
        
        self._save_metadata(metadata)
        return True
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a track from queue."""
        file_path = self.queue_dir / track_id
        
        try:
            if file_path.exists():
                file_path.unlink()
            
            # Remove from metadata
            metadata = self._load_metadata()
            if track_id in metadata:
                del metadata[track_id]
                self._save_metadata(metadata)

            # Emit event
            self._emit_track_event(
                EventType.QUEUE_UPDATED,
                track_id,
                {"action": "removed"},
            )

            return True
            
        except Exception:
            return False
    
    def search_tracks(self, query: str, fields: List[str] = None) -> List[Track]:
        """Search tracks in queue."""
        if fields is None:
            fields = ['title', 'artist', 'album', 'genre']
        
        all_tracks = self.get_tracks()
        matching_tracks = []
        
        query_lower = query.lower()
        
        for track in all_tracks:
            match = False
            for field in fields:
                value = getattr(track, field, None)
                if value and query_lower in value.lower():
                    match = True
                    break
            if match:
                matching_tracks.append(track)
        
        return matching_tracks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        tracks = self.get_tracks()
        total_duration = sum(t.duration for t in tracks if t.duration)
        total_size = sum(t.file_size for t in tracks if t.file_size)
        
        categories = {}
        for track in tracks:
            categories[track.category] = categories.get(track.category, 0) + 1
        
        return {
            "total_tracks": len(tracks),
            "total_duration_seconds": total_duration,
            "total_size_bytes": total_size,
            "categories": categories
        }
    
    def save_to_queue(self, name: str, data: bytes, category: str | None = None) -> Path:
        """Save uploaded file data to the sync queue directory."""
        queue = self.queue_dir
        if category:
            queue = queue / category
        queue.mkdir(parents=True, exist_ok=True)
        dest = queue / name
        with dest.open("wb") as fh:
            fh.write(data)
        logger.info("Saved %s to queue", dest)
        return dest

    def clear_queue(self) -> bool:
        """Remove all tracks from queue."""
        try:
            for file_path in self.queue_dir.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    file_path.unlink()
            
            # Clear metadata
            self._save_metadata({})
            return True
            
        except Exception:
            return False