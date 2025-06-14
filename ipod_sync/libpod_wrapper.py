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

try:  # pragma: no cover - the import will be mocked in tests
    import gpod  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    gpod = None
    logger.debug("python-gpod bindings not available")


def _get_db():
    """Return an open libgpod ``Database`` instance.

    Raises
    ------
    RuntimeError
        If the ``python-gpod`` bindings are not installed.
    """

    if gpod is None:
        raise RuntimeError("python-gpod bindings are required to use libpod_wrapper")

    logger.debug("Opening iPod database at %s", IPOD_MOUNT)
    return gpod.Database(str(IPOD_MOUNT))


def add_track(filepath: Path) -> str | None:
    """Import ``filepath`` into the iPod library.

    Parameters
    ----------
    filepath:
        Path to the audio file to import.  The file must already exist on the
        local filesystem.

    Returns
    -------
    str | None
        The database identifier assigned to the new track, if available.
    """

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(filepath)

    db = _get_db()
    logger.info("Importing %s", filepath)

    track = db.new_track(str(filepath))
    db.add_track(track)
    db.copy_delayed_files()
    db.close()

    return getattr(track, "dbid", None)


def delete_track(db_id: str) -> None:
    """Remove a track with the given database identifier from the iPod."""

    db = _get_db()
    logger.info("Deleting track %s", db_id)

    target = None
    for track in list(getattr(db, "tracks", [])):
        if str(getattr(track, "dbid", "")) == str(db_id):
            target = track
            break

    if target is None:
        db.close()
        raise KeyError(f"Track {db_id!r} not found")

    if hasattr(db, "remove_track"):
        db.remove_track(target)
    elif hasattr(db, "remove"):
        db.remove(target)

    db.copy_delayed_files()
    db.close()


def list_tracks() -> list[dict]:
    """Return a list of dictionaries describing the tracks on the iPod."""

    db = _get_db()
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

    db.close()
    return tracks


def list_playlists() -> list[dict]:
    """Return playlists on the iPod with their track IDs."""

    db = _get_db()
    logger.debug("Listing playlists from iPod")
    playlists = []
    for pl in getattr(db, "playlists", []):
        playlists.append(
            {
                "name": getattr(pl, "name", None),
                "tracks": [str(getattr(t, "dbid", "")) for t in getattr(pl, "tracks", [])],
            }
        )
    db.close()
    return playlists


def create_playlist(name: str, track_ids: list[str]) -> None:
    """Create a playlist containing the given track IDs."""

    db = _get_db()
    logger.info("Creating playlist %s", name)
    playlist = db.new_playlist(name)
    id_map = {str(getattr(t, "dbid", "")): t for t in getattr(db, "tracks", [])}

    for tid in track_ids:
        track = id_map.get(str(tid))
        if not track:
            continue
        if hasattr(playlist, "add_track"):
            playlist.add_track(track)
        elif hasattr(playlist, "add"):
            playlist.add(track)
        elif hasattr(db, "playlist_add_track"):
            db.playlist_add_track(playlist, track)

    if hasattr(db, "add_playlist"):
        db.add_playlist(playlist)
    elif hasattr(db, "add"):
        db.add(playlist)
    elif hasattr(db, "playlists"):
        db.playlists.append(playlist)

    db.copy_delayed_files()
    db.close()

