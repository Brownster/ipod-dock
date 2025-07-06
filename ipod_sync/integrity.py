"""File integrity and duplicate detection system inspired by gtkpod.

This module implements SHA1-based file integrity checking and duplicate
detection using algorithms adapted from the gtkpod project.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from .repositories import Track, Repository

logger = logging.getLogger(__name__)


class FileIntegrityManager:
    """File integrity and duplicate detection using gtkpod-inspired algorithms."""
    
    def __init__(self):
        self.hash_cache: Dict[str, str] = {}
        self.BLOCK_SIZE = 4096  # From gtkpod PATH_MAX_SHA1
        self.NUM_BLOCKS = 4     # From gtkpod NR_PATH_MAX_BLOCKS
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA1 hash using gtkpod's selective reading approach.
        
        This method reads specific blocks from the file rather than the entire
        file for performance, following gtkpod's approach for large files.
        """
        cache_key = str(file_path)
        if cache_key in self.hash_cache:
            return self.hash_cache[cache_key]
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        sha1_hash = hashlib.sha1()
        file_size = file_path.stat().st_size
        
        with open(file_path, 'rb') as f:
            # Read first blocks (like gtkpod)
            for _ in range(self.NUM_BLOCKS):
                block = f.read(self.BLOCK_SIZE)
                if not block:
                    break
                sha1_hash.update(block)
            
            # For larger files, also read from middle and end
            if file_size > self.BLOCK_SIZE * self.NUM_BLOCKS * 3:
                # Middle
                f.seek(file_size // 2)
                middle_block = f.read(self.BLOCK_SIZE)
                if middle_block:
                    sha1_hash.update(middle_block)
                
                # End
                f.seek(max(0, file_size - self.BLOCK_SIZE))
                end_block = f.read(self.BLOCK_SIZE)
                if end_block:
                    sha1_hash.update(end_block)
        
        result = sha1_hash.hexdigest()
        self.hash_cache[cache_key] = result
        logger.debug(f"Calculated hash for {file_path.name}: {result[:8]}...")
        return result
    
    def calculate_full_file_hash(self, file_path: Path) -> str:
        """Calculate complete SHA1 hash of entire file for critical operations."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        sha1_hash = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while True:
                block = f.read(self.BLOCK_SIZE)
                if not block:
                    break
                sha1_hash.update(block)
        
        return sha1_hash.hexdigest()
    
    async def find_duplicates_in_paths(self, file_paths: List[Path]) -> Dict[str, List[Path]]:
        """Find duplicate files among given paths using hash comparison."""
        hash_to_files: Dict[str, List[Path]] = {}
        
        for file_path in file_paths:
            if file_path.exists() and file_path.is_file():
                try:
                    file_hash = self.calculate_file_hash(file_path)
                    if file_hash not in hash_to_files:
                        hash_to_files[file_hash] = []
                    hash_to_files[file_hash].append(file_path)
                except Exception as e:
                    logger.warning(f"Failed to hash {file_path}: {e}")
        
        # Return only groups with duplicates
        duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
        
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicate file groups")
            for hash_val, files in duplicates.items():
                logger.info(f"Duplicate group {hash_val[:8]}: {[f.name for f in files]}")
        
        return duplicates
    
    async def find_duplicates_in_repository(self, repository: Repository) -> Dict[str, List[Track]]:
        """Find duplicate tracks in the repository using hash comparison."""
        all_tracks = await repository.get_tracks()
        hash_to_tracks: Dict[str, List[Track]] = {}
        
        for track in all_tracks:
            if track.file_path and hasattr(track, 'sha1_hash') and track.sha1_hash:
                if track.sha1_hash not in hash_to_tracks:
                    hash_to_tracks[track.sha1_hash] = []
                hash_to_tracks[track.sha1_hash].append(track)
        
        # Return only groups with duplicates
        duplicates = {h: tracks for h, tracks in hash_to_tracks.items() if len(tracks) > 1}
        
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicate track groups in repository")
        
        return duplicates
    
    async def verify_track_integrity(self, track: Track) -> bool:
        """Verify file hasn't changed since last hash calculation."""
        if not hasattr(track, 'sha1_hash') or not track.sha1_hash or not track.file_path:
            return False
        
        try:
            current_hash = self.calculate_file_hash(Path(track.file_path))
            return current_hash == track.sha1_hash
        except Exception as e:
            logger.warning(f"Failed to verify integrity for {track.file_path}: {e}")
            return False
    
    async def update_track_hash(self, track: Track) -> bool:
        """Update the SHA1 hash for a track."""
        if not track.file_path:
            return False
        
        try:
            file_path = Path(track.file_path)
            new_hash = self.calculate_file_hash(file_path)
            
            # Update track metadata if it has the sha1_hash attribute
            if hasattr(track, 'sha1_hash'):
                track.sha1_hash = new_hash
            
            # Update modification time if available
            if hasattr(track, 'mtime'):
                track.mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            logger.debug(f"Updated hash for {track.title}: {new_hash[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update hash for {track.title}: {e}")
            return False
    
    def clear_cache(self):
        """Clear the hash cache to free memory."""
        self.hash_cache.clear()
        logger.debug("Cleared hash cache")


class DuplicateResolver:
    """Handles resolution of duplicate files following gtkpod patterns."""
    
    def __init__(self, integrity_manager: FileIntegrityManager):
        self.integrity_manager = integrity_manager
    
    async def resolve_duplicate_files(self, duplicates: Dict[str, List[Path]], 
                                    strategy: str = "keep_largest") -> List[Path]:
        """Resolve duplicate files using specified strategy.
        
        Args:
            duplicates: Dictionary mapping hash to list of duplicate file paths
            strategy: Resolution strategy - 'keep_largest', 'keep_newest', 'keep_first'
            
        Returns:
            List of files that should be kept (others can be removed)
        """
        files_to_keep = []
        
        for hash_val, file_paths in duplicates.items():
            if len(file_paths) <= 1:
                files_to_keep.extend(file_paths)
                continue
            
            if strategy == "keep_largest":
                # Keep the largest file
                largest_file = max(file_paths, key=lambda p: p.stat().st_size)
                files_to_keep.append(largest_file)
                
            elif strategy == "keep_newest":
                # Keep the most recently modified file
                newest_file = max(file_paths, key=lambda p: p.stat().st_mtime)
                files_to_keep.append(newest_file)
                
            elif strategy == "keep_first":
                # Keep the first file (alphabetically)
                first_file = min(file_paths, key=str)
                files_to_keep.append(first_file)
            
            else:
                # Default: keep first file
                files_to_keep.append(file_paths[0])
            
            logger.info(f"Duplicate group {hash_val[:8]}: keeping {files_to_keep[-1].name}")
        
        return files_to_keep
    
    async def resolve_duplicate_tracks(self, duplicates: Dict[str, List[Track]], 
                                     repository: Repository,
                                     strategy: str = "keep_highest_quality") -> List[Track]:
        """Resolve duplicate tracks in repository.
        
        Args:
            duplicates: Dictionary mapping hash to list of duplicate tracks
            repository: Repository to update
            strategy: Resolution strategy
            
        Returns:
            List of tracks that should be kept
        """
        tracks_to_keep = []
        tracks_to_remove = []
        
        for hash_val, tracks in duplicates.items():
            if len(tracks) <= 1:
                tracks_to_keep.extend(tracks)
                continue
            
            if strategy == "keep_highest_quality":
                # Keep track with highest bitrate, or largest file if bitrate unavailable
                best_track = max(tracks, key=lambda t: (
                    getattr(t, 'bitrate', 0) or 0,
                    getattr(t, 'file_size', 0) or 0
                ))
                tracks_to_keep.append(best_track)
                tracks_to_remove.extend([t for t in tracks if t != best_track])
                
            elif strategy == "keep_newest":
                # Keep most recently added track
                newest_track = max(tracks, key=lambda t: getattr(t, 'date_added', datetime.min))
                tracks_to_keep.append(newest_track)
                tracks_to_remove.extend([t for t in tracks if t != newest_track])
            
            else:
                # Default: keep first track
                tracks_to_keep.append(tracks[0])
                tracks_to_remove.extend(tracks[1:])
            
            logger.info(f"Duplicate track group {hash_val[:8]}: keeping '{tracks_to_keep[-1].title}'")
        
        # Remove duplicate tracks from repository
        for track in tracks_to_remove:
            try:
                await repository.remove_track(track.id)
                logger.info(f"Removed duplicate track: {track.title}")
            except Exception as e:
                logger.error(f"Failed to remove duplicate track {track.title}: {e}")
        
        return tracks_to_keep


# Global instance for use across the application
file_integrity_manager = FileIntegrityManager()
duplicate_resolver = DuplicateResolver(file_integrity_manager)