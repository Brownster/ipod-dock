"""iPod repository implementation using libgpod."""
try:  # pragma: no cover - will be mocked in tests
    import gpod  # type: ignore
except Exception:  # pragma: no cover - missing optional dependency
    gpod = None
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from . import Repository, PlaylistRepository, Track, Playlist, TrackStatus
from .base_repository import EventEmittingRepository
from ..events import EventType
from .. import config

logger = logging.getLogger(__name__)

class IpodRepository(Repository, PlaylistRepository, EventEmittingRepository):
    """Repository for iPod data using libgpod."""
    
    def __init__(self, device_path: str = None):
        EventEmittingRepository.__init__(self, "IpodRepository")
        self.device_path = device_path or config.IPOD_DEVICE
        self._itdb = None
    
    def _ensure_connected(self):
        """Ensure iPod database is loaded."""
        if self._itdb is None:
            if gpod is None:
                raise RuntimeError("python-gpod is not installed")
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
    
    def _determine_category(self, gpod_track) -> str:
        """Determine track category from gpod track."""
        if gpod_track.mediatype == gpod.ITDB_MEDIATYPE_AUDIOBOOK:
            return "audiobook"
        elif gpod_track.mediatype == gpod.ITDB_MEDIATYPE_PODCAST:
            return "podcast"
        return "music"
    
    def _track_to_gpod_track(self, track: Track):
        """Convert our Track object to gpod track."""
        self._ensure_connected()
        gpod_track = gpod.Track()
        
        gpod_track.title = track.title
        gpod_track.artist = track.artist or ""
        gpod_track.album = track.album or ""
        gpod_track.genre = track.genre or ""
        gpod_track.track_nr = track.track_number or 0
        gpod_track.tracklen = (track.duration * 1000) if track.duration else 0
        gpod_track.size = track.file_size or 0
        gpod_track.bitrate = track.bitrate or 0
        gpod_track.playcount = track.play_count
        gpod_track.rating = track.rating * 20  # Convert 0-5 to 0-100
        
        # Set media type based on category
        if track.category == "audiobook":
            gpod_track.mediatype = gpod.ITDB_MEDIATYPE_AUDIOBOOK
        elif track.category == "podcast":
            gpod_track.mediatype = gpod.ITDB_MEDIATYPE_PODCAST
        else:
            gpod_track.mediatype = gpod.ITDB_MEDIATYPE_AUDIO
        
        return gpod_track
    
    def get_tracks(self, limit: Optional[int] = None, offset: int = 0) -> List[Track]:
        """Get all tracks from iPod."""
        self._ensure_connected()
        
        tracks = []
        gpod_tracks = list(self._itdb)
        
        # Apply offset and limit
        if offset > 0:
            gpod_tracks = gpod_tracks[offset:]
        if limit:
            gpod_tracks = gpod_tracks[:limit]
        
        for gpod_track in gpod_tracks:
            try:
                track = self._gpod_track_to_track(gpod_track)
                tracks.append(track)
            except Exception as e:
                logger.warning(f"Failed to convert track {gpod_track.dbid}: {e}")
        
        return tracks
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get a specific track by ID."""
        self._ensure_connected()
        
        try:
            dbid = int(track_id)
            gpod_track = self._itdb.get_track(dbid)
            if gpod_track:
                return self._gpod_track_to_track(gpod_track)
        except (ValueError, Exception) as e:
            logger.error(f"Failed to get track {track_id}: {e}")
        
        return None
    
    def add_track(self, track: Track) -> str:
        """Add a track to iPod."""
        self._ensure_connected()
        
        gpod_track = self._track_to_gpod_track(track)
        
        if track.file_path and Path(track.file_path).exists():
            # Copy file to iPod
            gpod_track.set_userdata('filename', track.file_path)
            self._itdb.new_playlist_for_track(gpod_track)
            self._itdb.copy_track_to_ipod(gpod_track, track.file_path)
        
        self._itdb.add(gpod_track)
        track_id = str(gpod_track.dbid)

        self._emit_track_event(
            EventType.TRACK_ADDED,
            track_id,
            {
                "title": track.title,
                "artist": track.artist,
                "category": track.category,
            },
        )

        return track_id
    
    def update_track(self, track: Track) -> bool:
        """Update an existing track."""
        self._ensure_connected()
        
        try:
            dbid = int(track.id)
            gpod_track = self._itdb.get_track(dbid)
            if not gpod_track:
                return False
            
            # Update fields
            gpod_track.title = track.title
            gpod_track.artist = track.artist or ""
            gpod_track.album = track.album or ""
            gpod_track.genre = track.genre or ""
            gpod_track.track_nr = track.track_number or 0
            gpod_track.playcount = track.play_count
            gpod_track.rating = track.rating * 20
            
            return True
            
        except (ValueError, Exception) as e:
            logger.error(f"Failed to update track {track.id}: {e}")
            return False
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a track from iPod."""
        self._ensure_connected()
        
        try:
            dbid = int(track_id)
            gpod_track = self._itdb.get_track(dbid)
            if gpod_track:
                self._itdb.remove(gpod_track, ipod=True)
                return True
        except (ValueError, Exception) as e:
            logger.error(f"Failed to remove track {track_id}: {e}")
        
        return False
    
    def search_tracks(self, query: str, fields: List[str] = None) -> List[Track]:
        """Search tracks by query."""
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
        """Get iPod statistics."""
        self._ensure_connected()
        
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
            "categories": categories,
            "total_playlists": len(self.get_playlists())
        }
    
    # Playlist methods
    def get_playlists(self) -> List[Playlist]:
        """Get all playlists from iPod."""
        self._ensure_connected()
        
        playlists = []
        for gpod_playlist in self._itdb.Playlists:
            if gpod_playlist.name == "iPod":  # Skip master playlist
                continue
                
            track_ids = [str(track.dbid) for track in gpod_playlist]
            
            playlist = Playlist(
                id=str(gpod_playlist.id),
                name=gpod_playlist.name,
                track_ids=track_ids,
                is_smart=gpod_playlist.is_spl,
                date_created=datetime.fromtimestamp(gpod_playlist.timestamp) if gpod_playlist.timestamp else None
            )
            playlists.append(playlist)
        
        return playlists
    
    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Get a specific playlist by ID."""
        playlists = self.get_playlists()
        for playlist in playlists:
            if playlist.id == playlist_id:
                return playlist
        return None
    
    def create_playlist(self, name: str, track_ids: List[str] = None) -> str:
        """Create a new playlist."""
        self._ensure_connected()
        
        gpod_playlist = gpod.Playlist(title=name)
        self._itdb.Playlists.add(gpod_playlist)
        
        if track_ids:
            self.add_tracks_to_playlist(str(gpod_playlist.id), track_ids)
        
        return str(gpod_playlist.id)
    
    def update_playlist(self, playlist: Playlist) -> bool:
        """Update an existing playlist."""
        # For now, just handle name changes
        self._ensure_connected()
        
        try:
            playlist_id = int(playlist.id)
            for gpod_playlist in self._itdb.Playlists:
                if gpod_playlist.id == playlist_id:
                    gpod_playlist.name = playlist.name
                    return True
        except (ValueError, Exception) as e:
            logger.error(f"Failed to update playlist {playlist.id}: {e}")
        
        return False
    
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist."""
        self._ensure_connected()
        
        try:
            playlist_id_int = int(playlist_id)
            for gpod_playlist in self._itdb.Playlists:
                if gpod_playlist.id == playlist_id_int:
                    self._itdb.Playlists.remove(gpod_playlist)
                    return True
        except (ValueError, Exception) as e:
            logger.error(f"Failed to delete playlist {playlist_id}: {e}")
        
        return False
    
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Add tracks to a playlist."""
        self._ensure_connected()
        
        try:
            playlist_id_int = int(playlist_id)
            gpod_playlist = None
            
            for pl in self._itdb.Playlists:
                if pl.id == playlist_id_int:
                    gpod_playlist = pl
                    break
            
            if not gpod_playlist:
                return False
            
            for track_id in track_ids:
                track_dbid = int(track_id)
                gpod_track = self._itdb.get_track(track_dbid)
                if gpod_track:
                    gpod_playlist.add(gpod_track)
            
            return True
            
        except (ValueError, Exception) as e:
            logger.error(f"Failed to add tracks to playlist {playlist_id}: {e}")
            return False
    
    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Remove tracks from a playlist."""
        self._ensure_connected()
        
        try:
            playlist_id_int = int(playlist_id)
            gpod_playlist = None
            
            for pl in self._itdb.Playlists:
                if pl.id == playlist_id_int:
                    gpod_playlist = pl
                    break
            
            if not gpod_playlist:
                return False
            
            for track_id in track_ids:
                track_dbid = int(track_id)
                gpod_track = self._itdb.get_track(track_dbid)
                if gpod_track and gpod_track in gpod_playlist:
                    gpod_playlist.remove(gpod_track)
            
            return True
            
        except (ValueError, Exception) as e:
            logger.error(f"Failed to remove tracks from playlist {playlist_id}: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Return ``True`` if the iPod appears to be connected."""
        if self._itdb:
            return True
        
        # Check device path
        if Path(self.device_path).exists():
            return True
        
        # Check mount point
        try:
            with open("/proc/mounts", "r", encoding="utf-8") as fh:
                for line in fh:
                    parts = line.split()
                    if parts and parts[0] == str(self.device_path):
                        return True
        except Exception:
            pass
            
        return False

    def save_changes(self) -> bool:
        """Save all changes to iPod."""
        if self._itdb:
            try:
                self._itdb.close()
                self._itdb = None  # Force reconnection on next operation
                return True
            except Exception as e:
                logger.error(f"Failed to save changes: {e}")
                return False
        return True