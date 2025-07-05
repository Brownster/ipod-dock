"""Local repository for managing local media library."""
from pathlib import Path
from typing import List, Optional

from .queue_repository import QueueRepository
from . import Track, TrackStatus
from .. import config


class LocalRepository(QueueRepository):
    """Repository for a local media library stored on disk."""

    def __init__(self, library_dir: Path | None = None):
        lib_dir = library_dir or config.UPLOADS_DIR
        super().__init__(lib_dir)
        self.queue_dir = lib_dir
        # Use a different metadata file name
        self.metadata_file = self.queue_dir / ".library_metadata.json"
        if not self.metadata_file.exists():
            self._save_metadata({})

    def get_tracks(self, limit: Optional[int] = None, offset: int = 0) -> List[Track]:
        tracks = super().get_tracks(limit=limit, offset=offset)
        for track in tracks:
            track.status = TrackStatus.ACTIVE
        return tracks
