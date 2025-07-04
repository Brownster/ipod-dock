"""Wrapper helpers around the :mod:`libgpod` Python bindings.

The real libgpod API is provided by the optional ``python-gpod`` package.  The
functions in this module keep the rest of the project decoupled from the
underlying library and make it easy to mock out libgpod in the unit tests.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .config import IPOD_MOUNT

logger = logging.getLogger(__name__)


class LibpodError(Exception):
    """Base exception for libpod_wrapper errors."""


try:  # pragma: no cover - the import will be mocked in tests
    import gpod  # type: ignore

    GpodException = gpod.GpodException
except (ImportError, AttributeError):  # pragma: no cover - handled at runtime
    gpod = None
    GpodException = None  # type: ignore
    logger.debug("python-gpod bindings not available")


def _get_db():
    """Return an open libgpod ``Database`` instance.

    Raises
    ------
    RuntimeError
        If the ``python-gpod`` bindings are not installed.
    LibpodError
        If the iPod database cannot be opened.
    """
    if gpod is None:
        raise RuntimeError("python-gpod bindings are required to use libpod_wrapper")

    logger.debug("Opening iPod database at %s", IPOD_MOUNT)
    try:
        return gpod.Database(str(IPOD_MOUNT))
    except GpodException as exc:
        raise LibpodError(f"Failed to open iPod database: {exc}") from exc


def add_track(filepath: Path) -> str | None:
    """Import ``filepath`` into the iPod library.

    Parameters
    ----------
    filepath:
        Path to the audio file to import.

    Returns
    -------
    str | None
        The database identifier assigned to the new track, if available.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(filepath)

    db = _get_db()
    try:
        logger.info("Importing %s", filepath)
        track = db.new_track(str(filepath))
        db.add_track(track)
        db.copy_delayed_files()
        return getattr(track, "dbid", None)
    except GpodException as exc:
        logger.error("gpod error adding track %s: %s", filepath, exc)
        raise LibpodError(f"Failed to add track {filepath.name}: {exc}") from exc
    finally:
        db.close()


def delete_track(db_id: str) -> None:
    """Remove a track with the given database identifier from the iPod."""
    db = _get_db()
    try:
        logger.info("Deleting track %s", db_id)
        target = None
        for track in list(getattr(db, "tracks", [])):
            if str(getattr(track, "dbid", "")) == str(db_id):
                target = track
                break

        if target is None:
            raise KeyError(f"Track {db_id!r} not found")

        db.remove_track(target)
        db.copy_delayed_files()
    except GpodException as exc:
        logger.error("gpod error deleting track %s: %s", db_id, exc)
        raise LibpodError(f"Failed to delete track {db_id}: {exc}") from exc
    finally:
        db.close()


def list_tracks() -> list[dict]:
    """Return a list of dictionaries describing the tracks on the iPod."""
    db = _get_db()
    try:
        logger.debug("Listing tracks from iPod")
        tracks = []
        for track in getattr(db, "tracks", []):
            tracks.append(
                {
                    "id": getattr(track, "dbid", None),
                    "title": getattr(track, "title", None),
                    "artist": getattr(track, "artist", None),
                    "album": getattr(track, "album", None),
                }
            )
        return tracks
    except GpodException as exc:
        raise LibpodError(f"Failed to list tracks: {exc}") from exc
    finally:
        db.close()


def list_playlists() -> list[dict]:
    """Return playlists on the iPod with their track IDs."""
    db = _get_db()
    try:
        logger.debug("Listing playlists from iPod")
        playlists = []
        for pl in getattr(db, "playlists", []):
            playlists.append(
                {
                    "name": getattr(pl, "name", None),
                    "tracks": [
                        str(getattr(t, "dbid", "")) for t in getattr(pl, "tracks", [])
                    ],
                }
            )
        return playlists
    except GpodException as exc:
        raise LibpodError(f"Failed to list playlists: {exc}") from exc
    finally:
        db.close()


def create_playlist(name: str, track_ids: list[str]) -> None:
    """Create a playlist containing the given track IDs."""
    db = _get_db()
    try:
        logger.info("Creating playlist %s", name)
        playlist = db.new_playlist(name)
        id_map = {str(getattr(t, "dbid", "")): t for t in getattr(db, "tracks", [])}

        for tid in track_ids:
            track = id_map.get(str(tid))
            if track:
                playlist.add_track(track)

        db.add_playlist(playlist)
        db.copy_delayed_files()
    except GpodException as exc:
        logger.error("gpod error creating playlist %s: %s", name, exc)
        raise LibpodError(f"Failed to create playlist {name}: {exc}") from exc
    finally:
        db.close()

