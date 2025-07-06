"""Comprehensive metadata extraction system inspired by gtkpod's multi-format support.

This module provides extensive metadata extraction capabilities for various
audio formats, following patterns from gtkpod's plugin-based approach.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import mimetypes

try:
    import mutagen
    from mutagen.id3 import ID3NoHeaderError
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    from mutagen.wave import WAVE
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    mutagen = None

from .repositories import Track
from . import config

logger = logging.getLogger(__name__)


class MetadataExtractor(ABC):
    """Base class for format-specific metadata extractors."""
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this extractor supports."""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from the given file."""
        pass
    
    def get_duration_ms(self, file_path: Path) -> Optional[int]:
        """Get duration in milliseconds."""
        return None


class MP3Extractor(MetadataExtractor):
    """MP3 metadata extractor using mutagen."""
    
    def get_supported_extensions(self) -> List[str]:
        return ['.mp3']
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract comprehensive MP3 metadata following gtkpod patterns."""
        metadata = {}
        
        if not MUTAGEN_AVAILABLE:
            return metadata
        
        try:
            audio = MP3(file_path)
            
            # Basic metadata
            metadata.update({
                'title': self._get_text_frame(audio, 'TIT2'),
                'artist': self._get_text_frame(audio, 'TPE1'),
                'album': self._get_text_frame(audio, 'TALB'),
                'albumartist': self._get_text_frame(audio, 'TPE2'),
                'composer': self._get_text_frame(audio, 'TCOM'),
                'genre': self._get_text_frame(audio, 'TCON'),
                'year': self._get_year(audio),
                'comment': self._get_text_frame(audio, 'COMM::eng'),
            })
            
            # Track and disc numbers
            track_info = self._get_text_frame(audio, 'TRCK')
            if track_info and '/' in track_info:
                track_num, track_total = track_info.split('/', 1)
                metadata['track_number'] = self._safe_int(track_num)
                metadata['track_total'] = self._safe_int(track_total)
            elif track_info:
                metadata['track_number'] = self._safe_int(track_info)
            
            disc_info = self._get_text_frame(audio, 'TPOS')
            if disc_info and '/' in disc_info:
                disc_num, disc_total = disc_info.split('/', 1)
                metadata['disc_number'] = self._safe_int(disc_num)
                metadata['disc_total'] = self._safe_int(disc_total)
            elif disc_info:
                metadata['disc_number'] = self._safe_int(disc_info)
            
            # Sort fields (gtkpod style)
            metadata.update({
                'sort_title': self._get_text_frame(audio, 'TSOT'),
                'sort_artist': self._get_text_frame(audio, 'TSOP'),
                'sort_album': self._get_text_frame(audio, 'TSOA'),
                'sort_albumartist': self._get_text_frame(audio, 'TSO2'),
            })
            
            # Extended fields
            metadata.update({
                'bpm': self._safe_int(self._get_text_frame(audio, 'TBPM')),
                'compilation': self._get_text_frame(audio, 'TCMP') == '1',
                'subtitle': self._get_text_frame(audio, 'TIT3'),
                'description': self._get_text_frame(audio, 'TIT1'),
                'podcasturl': self._get_text_frame(audio, 'WOAS'),
            })
            
            # Technical info
            if hasattr(audio, 'info'):
                metadata.update({
                    'duration_ms': int(audio.info.length * 1000) if audio.info.length else None,
                    'bitrate': getattr(audio.info, 'bitrate', None),
                    'sample_rate': getattr(audio.info, 'sample_rate', None),
                })
            
            # Lyrics
            lyrics_frame = audio.get('USLT::eng')
            if lyrics_frame:
                metadata['lyrics'] = str(lyrics_frame.text)
            
        except Exception as e:
            logger.warning(f"Failed to extract MP3 metadata from {file_path}: {e}")
        
        return metadata
    
    def _get_text_frame(self, audio, frame_id: str) -> Optional[str]:
        """Get text from ID3 frame."""
        frame = audio.get(frame_id)
        if frame:
            return str(frame.text[0]) if frame.text else None
        return None
    
    def _get_year(self, audio) -> Optional[int]:
        """Extract year from various date fields."""
        # Try TDRC first (recording time)
        year_frame = audio.get('TDRC')
        if year_frame and year_frame.text:
            try:
                return int(str(year_frame.text[0])[:4])
            except (ValueError, IndexError):
                pass
        
        # Fallback to TYER (year)
        year_frame = audio.get('TYER')
        if year_frame and year_frame.text:
            try:
                return int(str(year_frame.text[0]))
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


class FLACExtractor(MetadataExtractor):
    """FLAC metadata extractor."""
    
    def get_supported_extensions(self) -> List[str]:
        return ['.flac']
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract FLAC metadata."""
        metadata = {}
        
        if not MUTAGEN_AVAILABLE:
            return metadata
        
        try:
            audio = FLAC(file_path)
            
            # Basic metadata
            metadata.update({
                'title': self._get_vorbis_field(audio, 'title'),
                'artist': self._get_vorbis_field(audio, 'artist'),
                'album': self._get_vorbis_field(audio, 'album'),
                'albumartist': self._get_vorbis_field(audio, 'albumartist'),
                'composer': self._get_vorbis_field(audio, 'composer'),
                'genre': self._get_vorbis_field(audio, 'genre'),
                'year': self._safe_int(self._get_vorbis_field(audio, 'date')),
                'comment': self._get_vorbis_field(audio, 'comment'),
                'track_number': self._safe_int(self._get_vorbis_field(audio, 'tracknumber')),
                'track_total': self._safe_int(self._get_vorbis_field(audio, 'tracktotal')),
                'disc_number': self._safe_int(self._get_vorbis_field(audio, 'discnumber')),
                'disc_total': self._safe_int(self._get_vorbis_field(audio, 'disctotal')),
            })
            
            # Technical info
            if hasattr(audio, 'info'):
                metadata.update({
                    'duration_ms': int(audio.info.length * 1000) if audio.info.length else None,
                    'bitrate': getattr(audio.info, 'bitrate', None),
                    'sample_rate': getattr(audio.info, 'sample_rate', None),
                })
            
        except Exception as e:
            logger.warning(f"Failed to extract FLAC metadata from {file_path}: {e}")
        
        return metadata
    
    def _get_vorbis_field(self, audio, field: str) -> Optional[str]:
        """Get field from vorbis comment."""
        values = audio.get(field.upper(), [])
        return values[0] if values else None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(str(value).split('/')[0])  # Handle "1/10" format
        except (ValueError, TypeError):
            return None


class M4AExtractor(MetadataExtractor):
    """M4A/MP4 metadata extractor."""
    
    def get_supported_extensions(self) -> List[str]:
        return ['.m4a', '.m4b', '.mp4', '.aac']
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract M4A metadata."""
        metadata = {}
        
        if not MUTAGEN_AVAILABLE:
            return metadata
        
        try:
            audio = MP4(file_path)
            
            # MP4 atom mapping
            metadata.update({
                'title': self._get_mp4_field(audio, '©nam'),
                'artist': self._get_mp4_field(audio, '©ART'),
                'album': self._get_mp4_field(audio, '©alb'),
                'albumartist': self._get_mp4_field(audio, 'aART'),
                'composer': self._get_mp4_field(audio, '©wrt'),
                'genre': self._get_mp4_field(audio, '©gen'),
                'year': self._safe_int(self._get_mp4_field(audio, '©day')),
                'comment': self._get_mp4_field(audio, '©cmt'),
                'description': self._get_mp4_field(audio, 'desc'),
                'lyrics': self._get_mp4_field(audio, '©lyr'),
            })
            
            # Track numbers
            track_info = audio.get('trkn')
            if track_info and len(track_info[0]) >= 2:
                metadata['track_number'] = track_info[0][0]
                metadata['track_total'] = track_info[0][1]
            
            # Disc numbers  
            disc_info = audio.get('disk')
            if disc_info and len(disc_info[0]) >= 2:
                metadata['disc_number'] = disc_info[0][0]
                metadata['disc_total'] = disc_info[0][1]
            
            # Technical info
            if hasattr(audio, 'info'):
                metadata.update({
                    'duration_ms': int(audio.info.length * 1000) if audio.info.length else None,
                    'bitrate': getattr(audio.info, 'bitrate', None),
                    'sample_rate': getattr(audio.info, 'sample_rate', None),
                })
            
        except Exception as e:
            logger.warning(f"Failed to extract M4A metadata from {file_path}: {e}")
        
        return metadata
    
    def _get_mp4_field(self, audio, atom: str) -> Optional[str]:
        """Get field from MP4 atom."""
        values = audio.get(atom, [])
        return str(values[0]) if values else None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(str(value)[:4])  # Handle date strings
        except (ValueError, TypeError):
            return None


class OggExtractor(MetadataExtractor):
    """OGG Vorbis metadata extractor."""
    
    def get_supported_extensions(self) -> List[str]:
        return ['.ogg', '.oga']
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract OGG metadata."""
        metadata = {}
        
        if not MUTAGEN_AVAILABLE:
            return metadata
        
        try:
            audio = OggVorbis(file_path)
            
            # Same as FLAC (uses vorbis comments)
            metadata.update({
                'title': self._get_vorbis_field(audio, 'title'),
                'artist': self._get_vorbis_field(audio, 'artist'),
                'album': self._get_vorbis_field(audio, 'album'),
                'albumartist': self._get_vorbis_field(audio, 'albumartist'),
                'composer': self._get_vorbis_field(audio, 'composer'),
                'genre': self._get_vorbis_field(audio, 'genre'),
                'year': self._safe_int(self._get_vorbis_field(audio, 'date')),
                'comment': self._get_vorbis_field(audio, 'comment'),
                'track_number': self._safe_int(self._get_vorbis_field(audio, 'tracknumber')),
                'track_total': self._safe_int(self._get_vorbis_field(audio, 'tracktotal')),
            })
            
            # Technical info
            if hasattr(audio, 'info'):
                metadata.update({
                    'duration_ms': int(audio.info.length * 1000) if audio.info.length else None,
                    'bitrate': getattr(audio.info, 'bitrate', None),
                    'sample_rate': getattr(audio.info, 'sample_rate', None),
                })
            
        except Exception as e:
            logger.warning(f"Failed to extract OGG metadata from {file_path}: {e}")
        
        return metadata
    
    def _get_vorbis_field(self, audio, field: str) -> Optional[str]:
        """Get field from vorbis comment."""
        values = audio.get(field.upper(), [])
        return values[0] if values else None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(str(value).split('/')[0])
        except (ValueError, TypeError):
            return None


class MetadataExtractionService:
    """Comprehensive metadata extraction service following gtkpod patterns."""
    
    def __init__(self):
        self.extractors = {
            'mp3': MP3Extractor(),
            'flac': FLACExtractor(),
            'm4a': M4AExtractor(),
            'm4b': M4AExtractor(),  # Same as M4A
            'mp4': M4AExtractor(),
            'aac': M4AExtractor(),
            'ogg': OggExtractor(),
            'oga': OggExtractor(),
        }
    
    def extract_comprehensive_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract comprehensive metadata using appropriate extractor."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = file_path.suffix.lower().lstrip('.')
        extractor = self.extractors.get(file_ext)
        
        if not extractor:
            logger.warning(f"No extractor available for {file_ext} files")
            return {}
        
        metadata = extractor.extract_metadata(file_path)
        
        # Add file system metadata
        file_stat = file_path.stat()
        metadata.update({
            'file_path': str(file_path),
            'pc_path_utf8': str(file_path),
            'file_size': file_stat.st_size,
            'mtime': datetime.fromtimestamp(file_stat.st_mtime),
            'orig_filesize': file_stat.st_size,
        })
        
        # Clean up None values and ensure correct types
        cleaned_metadata = {}
        for key, value in metadata.items():
            if value is not None and value != '':
                cleaned_metadata[key] = value
        
        return cleaned_metadata
    
    def create_track_from_file(self, file_path: Path, track_id: str = None) -> Track:
        """Create a Track object from file with comprehensive metadata."""
        from .integrity import file_integrity_manager
        
        metadata = self.extract_comprehensive_metadata(file_path)
        
        # Calculate SHA1 hash
        try:
            sha1_hash = file_integrity_manager.calculate_file_hash(file_path)
            metadata['sha1_hash'] = sha1_hash
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
        
        # Create track ID if not provided
        if not track_id:
            track_id = f"track_{sha1_hash[:16]}" if sha1_hash else f"track_{file_path.stem}"
        
        # Map duration from milliseconds to seconds
        duration_seconds = None
        if metadata.get('duration_ms'):
            duration_seconds = metadata['duration_ms'] // 1000
        
        # Determine category based on file extension and metadata
        category = self._determine_category(file_path, metadata)
        
        return Track(
            id=track_id,
            title=metadata.get('title') or file_path.stem,
            artist=metadata.get('artist'),
            album=metadata.get('album'),
            genre=metadata.get('genre'),
            track_number=metadata.get('track_number'),
            duration=duration_seconds,
            file_path=str(file_path),
            file_size=metadata.get('file_size'),
            bitrate=metadata.get('bitrate'),
            sample_rate=metadata.get('sample_rate'),
            date_added=datetime.now(),
            play_count=0,
            rating=0,
            status=TrackStatus.PENDING,
            category=category,
            
            # Extended metadata
            pc_path_utf8=metadata.get('pc_path_utf8'),
            mtime=metadata.get('mtime'),
            orig_filesize=metadata.get('orig_filesize'),
            sha1_hash=metadata.get('sha1_hash'),
            lyrics=metadata.get('lyrics'),
            
            # Additional metadata
            year=metadata.get('year'),
            track_total=metadata.get('track_total'),
            disc_number=metadata.get('disc_number'),
            disc_total=metadata.get('disc_total'),
            composer=metadata.get('composer'),
            albumartist=metadata.get('albumartist'),
            bpm=metadata.get('bpm'),
            compilation=metadata.get('compilation'),
            
            # Sort fields
            sort_artist=metadata.get('sort_artist'),
            sort_title=metadata.get('sort_title'),
            sort_album=metadata.get('sort_album'),
            sort_albumartist=metadata.get('sort_albumartist'),
            
            # Podcast/audiobook fields
            description=metadata.get('description'),
            podcasturl=metadata.get('podcasturl'),
            podcastrss=metadata.get('podcastrss'),
            subtitle=metadata.get('subtitle'),
            
            # Sync tracking
            sync_status="pending",
            last_synced=None,
            sync_error=None
        )
    
    def _determine_category(self, file_path: Path, metadata: Dict[str, Any]) -> str:
        """Determine track category based on file and metadata."""
        file_ext = file_path.suffix.lower()
        
        # Check file extension first
        if file_ext in ['.m4b']:
            return "audiobook"
        
        # Check genre for hints
        genre = metadata.get('genre', '').lower()
        if 'podcast' in genre:
            return "podcast"
        elif 'audiobook' in genre or 'spoken' in genre:
            return "audiobook"
        
        # Check if it's in a podcast/audiobook directory
        path_str = str(file_path).lower()
        if 'podcast' in path_str:
            return "podcast"
        elif 'audiobook' in path_str or 'book' in path_str:
            return "audiobook"
        
        # Default to music
        return "music"
    
    def is_supported_format(self, file_path: Path) -> bool:
        """Check if file format is supported."""
        file_ext = file_path.suffix.lower().lstrip('.')
        return file_ext in self.extractors
    
    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions."""
        extensions = []
        for extractor in self.extractors.values():
            extensions.extend(extractor.get_supported_extensions())
        return sorted(set(extensions))


# Global instance for use across the application
metadata_service = MetadataExtractionService()