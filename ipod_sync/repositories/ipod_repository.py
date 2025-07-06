"""iPod repository implementation using libgpod."""
try:  # pragma: no cover - will be mocked in tests
    import gpod  # type: ignore
except Exception:  # pragma: no cover - missing optional dependency
    gpod = None
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import shutil
import os

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
        """Ensure iPod database is loaded with comprehensive error handling."""
        if self._itdb is None:
            if gpod is None:
                raise RuntimeError("python-gpod is not installed. Install with: apt-get install python3-gpod")
            
            mount_point = str(config.IPOD_MOUNT)
            
            # Validate mount point exists
            if not Path(mount_point).exists():
                raise RuntimeError(f"iPod mount point does not exist: {mount_point}")
            
            # Check if it's actually mounted
            try:
                with open("/proc/mounts", "r", encoding="utf-8") as fh:
                    mounted = any(mount_point in line for line in fh)
                    if not mounted:
                        logger.warning(f"iPod may not be mounted at {mount_point}")
            except Exception:
                pass  # Non-critical check
            
            try:
                self._itdb = gpod.Database(mount_point)
                logger.info(f"Connected to iPod at {mount_point}")
                
                # Validate database structure
                if not hasattr(self._itdb, 'Playlists') or len(self._itdb.Playlists) == 0:
                    logger.warning("iPod database appears to have no playlists. Database may be corrupted.")
                    
            except Exception as e:
                # Check for specific gpod exceptions
                if "Unable to parse iTunes database" in str(e):
                    raise RuntimeError(f"Failed to parse iPod database at {mount_point}: {e}. iPod may not be properly mounted or database may be corrupted.")
                else:
                    raise RuntimeError(f"Failed to connect to iPod: {e}")
    
    def _create_gpod_track_from_file(self, file_path: str):
        """Create a gpod track from file with Python 2/3 compatibility.
        
        The gpod.Track(filename) constructor has issues in Python 3 due to
        map() iterator vs list incompatibility. This function provides a
        robust fallback mechanism.
        """
        if gpod is None:
            raise RuntimeError("python-gpod is not installed")
        
        try:
            # Try the direct constructor first (works in some Python 3 environments)
            return gpod.Track(file_path)
        except (TypeError, AttributeError) as e:
            logger.warning(f"gpod.Track(filename) failed: {e}. Using fallback method.")
            
            # Fallback: Create empty track and manually set file path
            track = gpod.Track()
            
            # Initialize userdata if not present
            try:
                if track['userdata'] is None:
                    track['userdata'] = {}
            except (KeyError, TypeError):
                track['userdata'] = {}
            
            # Set the file path in userdata
            track['userdata']['filename'] = file_path
            
            # Extract basic metadata using mutagen or similar if available
            try:
                from .. import metadata
                meta = metadata.extract_metadata(file_path)
                
                # Set metadata from extracted info
                if meta.get('title'):
                    track['title'] = meta['title']
                if meta.get('artist'):
                    track['artist'] = meta['artist']
                if meta.get('album'):
                    track['album'] = meta['album']
                if meta.get('genre'):
                    track['genre'] = meta['genre']
                if meta.get('track_number'):
                    track['track_nr'] = meta['track_number']
                if meta.get('duration'):
                    track['tracklen'] = int(meta['duration'] * 1000)  # Convert to milliseconds
                    
                # Set file size
                if os.path.exists(file_path):
                    track['size'] = os.path.getsize(file_path)
                    
            except Exception as meta_error:
                logger.warning(f"Failed to extract metadata from {file_path}: {meta_error}")
                # Set basic info from filename
                track['title'] = Path(file_path).stem
                if os.path.exists(file_path):
                    track['size'] = os.path.getsize(file_path)
            
            return track
    
    def _gpod_track_to_track(self, gpod_track) -> Track:
        """Convert gpod track to our Track object using proper attribute access."""
        # Use dictionary-style access for gpod tracks
        # Note: gpod tracks don't have .get() method, use direct access with try/except
        
        def _safe_get_str(track, key):
            """Safely get string value from gpod track with proper encoding."""
            try:
                value = track[key]
                if isinstance(value, bytes):
                    return value.decode('utf-8', errors='replace')
                return value
            except (KeyError, TypeError):
                return None
        
        def _safe_get_int(track, key, default=None):
            """Safely get integer value from gpod track."""
            try:
                return track[key] or default
            except (KeyError, TypeError):
                return default
        
        title = _safe_get_str(gpod_track, 'title') or "Unknown"
        artist = _safe_get_str(gpod_track, 'artist')
        album = _safe_get_str(gpod_track, 'album')
        genre = _safe_get_str(gpod_track, 'genre')
        ipod_path = _safe_get_str(gpod_track, 'ipod_path')
        
        # Handle track number
        track_number = _safe_get_int(gpod_track, 'track_nr')
        
        # Handle duration (convert from milliseconds to seconds)
        tracklen = _safe_get_int(gpod_track, 'tracklen', 0)
        duration = tracklen // 1000 if tracklen else None
        
        # Handle file size and bitrate
        file_size = _safe_get_int(gpod_track, 'size')
        bitrate = _safe_get_int(gpod_track, 'bitrate')
        
        # Handle timestamps
        date_added = None
        date_modified = None
        try:
            if gpod_track['time_added']:
                date_added = datetime.fromtimestamp(gpod_track['time_added'])
        except (KeyError, TypeError, ValueError):
            pass
        
        try:
            if gpod_track['time_modified']:
                date_modified = datetime.fromtimestamp(gpod_track['time_modified'])
        except (KeyError, TypeError, ValueError):
            pass
        
        # Handle play count and rating
        play_count = _safe_get_int(gpod_track, 'playcount', 0)
        rating_raw = _safe_get_int(gpod_track, 'rating', 0)
        rating = rating_raw // 20 if rating_raw else 0  # Convert 0-100 to 0-5
        
        return Track(
            id=str(gpod_track['dbid']),
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            track_number=track_number,
            duration=duration,
            file_path=ipod_path,
            file_size=file_size,
            bitrate=bitrate,
            date_added=date_added,
            date_modified=date_modified,
            play_count=play_count,
            rating=rating,
            status=TrackStatus.ACTIVE,
            category=self._determine_category(gpod_track),
            metadata={
                "dbid": gpod_track['dbid'],
                "compilation": _safe_get_int(gpod_track, 'compilation'),
                "year": _safe_get_int(gpod_track, 'year'),
                "bpm": _safe_get_int(gpod_track, 'BPM'),
                "cd_nr": _safe_get_int(gpod_track, 'cd_nr'),
                "cds": _safe_get_int(gpod_track, 'cds')
            }
        )
    
    def _determine_category(self, gpod_track) -> str:
        """Determine track category from gpod track."""
        try:
            mediatype = gpod_track['mediatype'] or 0
            if mediatype == gpod.ITDB_MEDIATYPE_AUDIOBOOK:
                return "audiobook"
            elif mediatype == gpod.ITDB_MEDIATYPE_PODCAST:
                return "podcast"
            return "music"
        except (KeyError, AttributeError, TypeError):
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
        """Add a track to iPod using robust Python 2/3 compatible patterns."""
        self._ensure_connected()
        
        # Comprehensive validation
        if not track:
            raise ValueError("Track object is required")
        
        if not track.file_path:
            raise ValueError("Track file_path is required")
        
        file_path = Path(track.file_path)
        if not file_path.exists():
            raise ValueError(f"File path does not exist: {track.file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {track.file_path}")
        
        # Check file size (reasonable limits)
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"File is empty: {track.file_path}")
        
        if file_size > 500 * 1024 * 1024:  # 500MB limit
            logger.warning(f"Large file detected ({file_size / 1024 / 1024:.1f}MB): {track.file_path}")
        
        # Validate file extension
        supported_extensions = {'.mp3', '.m4a', '.m4b', '.aac', '.wav', '.flac'}
        if file_path.suffix.lower() not in supported_extensions:
            logger.warning(f"Unsupported file extension {file_path.suffix}: {track.file_path}")
        
        # Validate track metadata
        if not track.title or track.title.strip() == "":
            logger.warning(f"Track has no title, using filename: {file_path.stem}")
            track.title = file_path.stem
        
        try:
            # Create track using our robust wrapper function
            gpod_track = self._create_gpod_track_from_file(track.file_path)
            logger.debug("Created gpod track from file: %s", track.file_path)
            
            # Override with our metadata if provided
            if track.title:
                gpod_track['title'] = track.title
            if track.artist:
                gpod_track['artist'] = track.artist
            if track.album:
                gpod_track['album'] = track.album
            if track.genre:
                gpod_track['genre'] = track.genre
            if track.track_number:
                gpod_track['track_nr'] = track.track_number
            if track.rating:
                gpod_track['rating'] = track.rating * 20  # Convert 0-5 to 0-100
            
            # Set media type based on category and file extension (following gtkpod patterns)
            file_ext = Path(track.file_path).suffix.lower()
            
            if track.category == "audiobook" or file_ext == '.m4b':
                gpod_track['mediatype'] = gpod.ITDB_MEDIATYPE_AUDIOBOOK
                # Set audiobook-specific properties (from gtkpod)
                gpod_track['remember_playback_position'] = 1
                gpod_track['skip_when_shuffling'] = 1
                logger.debug(f"Set as audiobook with remember_playback_position and skip_when_shuffling")
            elif track.category == "podcast":
                gpod_track['mediatype'] = gpod.ITDB_MEDIATYPE_PODCAST
                # Set podcast-specific properties (from gtkpod)
                gpod_track['remember_playback_position'] = 1
                gpod_track['skip_when_shuffling'] = 1
                logger.debug(f"Set as podcast with remember_playback_position and skip_when_shuffling")
            else:
                gpod_track['mediatype'] = gpod.ITDB_MEDIATYPE_AUDIO
                logger.debug(f"Set as regular audio/music")
            
            # Add track to database first (required before copy_to_ipod)
            self._itdb.add(gpod_track)
            logger.debug("Added track to database with dbid: %s", gpod_track['dbid'])
            
            # Copy file to iPod - handle both automatic and manual copying
            try:
                gpod_track.copy_to_ipod()
                ipod_path = gpod_track['ipod_path']
                logger.info("Copied file to iPod using copy_to_ipod(): %s -> %s", track.file_path, ipod_path)
            except Exception as copy_error:
                logger.warning("copy_to_ipod() failed: %s. Using manual copy.", copy_error)
                
                # Manual copy as fallback
                music_dir = os.path.join(str(config.IPOD_MOUNT), 'iPod_Control', 'Music')
                
                # Find or create a music folder
                folders = [f for f in os.listdir(music_dir) if f.startswith('F') and f[1:].isdigit()]
                if folders:
                    folder_name = folders[0]  # Use first available folder
                else:
                    folder_name = 'F00'
                    folder_path = os.path.join(music_dir, folder_name)
                    os.makedirs(folder_path, exist_ok=True)
                
                # Generate unique filename
                import time
                dest_filename = f"track_{int(time.time())}.{Path(track.file_path).suffix[1:]}"
                dest_path = os.path.join(music_dir, folder_name, dest_filename)
                
                # Copy file
                shutil.copy2(track.file_path, dest_path)
                
                # Update track with file path
                gpod_track['userdata']['filename'] = dest_path
                gpod_track['ipod_path'] = dest_path
                ipod_path = dest_path
                
                logger.info("Manually copied file to iPod: %s -> %s", track.file_path, dest_path)
            
            # Add to main playlist (first playlist is usually the master playlist)
            if len(self._itdb.Playlists) > 0:
                main_playlist = self._itdb.Playlists[0]
                main_playlist.add(gpod_track)
                logger.debug("Added track to main playlist: %s", main_playlist.name)
            
            track_id = str(gpod_track['dbid'])
            
            self._emit_track_event(
                EventType.TRACK_ADDED,
                track_id,
                {
                    "title": gpod_track['title'] or track.title,
                    "artist": gpod_track['artist'] or track.artist,
                    "category": track.category,
                    "file_path": ipod_path,
                },
            )
            
            return track_id
            
        except Exception as e:
            logger.error("Failed to add track %s: %s", track.file_path, e)
            raise
    
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
        """Remove a track from iPod using proper track lookup."""
        self._ensure_connected()
        
        try:
            dbid = int(track_id)
            
            # Find track by iterating through master playlist (Database doesn't have get_track)
            master = self._itdb.get_master()
            target_track = None
            
            for track in list(master):
                if track['dbid'] == dbid:
                    target_track = track
                    break
            
            if target_track:
                # Get track info for logging
                title = target_track['title']
                if isinstance(title, bytes):
                    title = title.decode('utf-8', errors='replace')
                
                # Remove track from database
                self._itdb.remove(target_track)
                logger.info(f"Removed track from iPod: {title} (ID: {track_id})")
                
                # Emit removal event
                try:
                    artist = target_track['artist']
                    if isinstance(artist, bytes):
                        artist = artist.decode('utf-8', errors='replace')
                except (KeyError, TypeError):
                    artist = 'Unknown'
                
                self._emit_track_event(
                    EventType.TRACK_REMOVED,
                    track_id,
                    {
                        "title": title,
                        "artist": artist,
                    },
                )
                
                return True
            else:
                logger.warning(f"Track with ID {track_id} not found")
                return False
                
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
        """Save all changes to iPod database."""
        if self._itdb:
            try:
                # Use close() method to save changes - this is the correct pattern
                self._itdb.close()
                logger.info("Saved changes to iPod database")
                self._itdb = None  # Force reconnection on next operation
                return True
            except Exception as e:
                logger.error(f"Failed to save changes: {e}")
                return False
        return True