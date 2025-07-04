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

    GpodException = gpod.DatabaseException
except ImportError:  # pragma: no cover - handled at runtime
    gpod = None
    class GpodException(Exception):
        pass
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
        if hasattr(db, "new_Track"):
            track = db.new_Track(filename=str(filepath))
        elif hasattr(db, "new_track"):
            track = db.new_track(str(filepath))
        elif hasattr(gpod, "Track"):
            track = gpod.Track(filename=str(filepath))
        else:
            raise LibpodError("No supported track creation method found")

        if hasattr(track, "copy_to_ipod"):
            track.copy_to_ipod()

        if hasattr(db, "add"):
            db.add(track)
        else:
            db.add_track(track)
        db.copy_delayed_files()
        db_id = getattr(track, 'dbid', None)
        if db_id is None and hasattr(track, '__getitem__'):
            try:
                db_id = track['dbid']
            except Exception:
                db_id = None
        return db_id
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
        if hasattr(db, 'get_master'):
            master = db.get_master()
        else:
            master = getattr(db, 'tracks', [])
        for track in list(master):
            tid = None
            if hasattr(track, '__getitem__'):
                try:
                    tid = track['dbid']
                except Exception:
                    tid = None
            if tid is None:
                tid = getattr(track, 'dbid', None)
            if str(tid) == str(db_id):
                target = track
                break

        if target is None:
            raise KeyError(f"Track {db_id!r} not found")

        if hasattr(db, "remove"):
            db.remove(target)
        else:
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
        if hasattr(db, 'get_master'):
            master = db.get_master()
        else:
            master = getattr(db, 'tracks', [])
        for track in list(master):
            def _field(name):
                if hasattr(track, '__getitem__'):
                    try:
                        val = track[name]
                    except Exception:
                        val = None
                else:
                    val = getattr(track, name, None)
                if isinstance(val, bytes):
                    val = val.decode('utf-8')
                return val

            tracks.append({
                "id": str(_field('dbid')) if _field('dbid') is not None else None,
                "title": _field('title'),
                "artist": _field('artist'),
                "album": _field('album'),
            })
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
        playlists_src = db.get_playlists() if hasattr(db, 'get_playlists') else getattr(db, 'playlists', [])
        for pl in playlists_src:
            def _pl_field(obj, name):
                if hasattr(obj, '__getitem__'):
                    try:
                        val = obj[name]
                    except Exception:
                        val = None
                else:
                    val = getattr(obj, name, None)
                if isinstance(val, bytes):
                    val = val.decode('utf-8')
                return val

            if hasattr(pl, '__iter__'):
                tracks_src = list(pl)
            else:
                tracks_src = getattr(pl, 'tracks', [])
            tracks = []
            for t in tracks_src:
                tid = _pl_field(t, 'dbid')
                tracks.append(str(tid) if tid is not None else None)

            playlists.append({
                "name": _pl_field(pl, 'name'),
                "tracks": tracks,
            })
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
        if hasattr(db, "new_Playlist"):
            playlist = db.new_Playlist()
            if hasattr(playlist, "name"):
                playlist.name = name.encode("utf-8")
        elif hasattr(db, "new_playlist"):
            try:
                playlist = db.new_playlist(name)
            except TypeError:
                playlist = db.new_playlist()
                if hasattr(playlist, "name"):
                    playlist.name = name.encode("utf-8")
        else:
            raise LibpodError("No supported playlist creation method found")
        if hasattr(db, 'get_master'):
            master = db.get_master()
        else:
            master = getattr(db, 'tracks', [])
        id_map = {}
        for t in list(master):
            tid = None
            if hasattr(t, '__getitem__'):
                try:
                    tid = t['dbid']
                except Exception:
                    tid = None
            if tid is None:
                tid = getattr(t, 'dbid', None)
            if tid is not None:
                id_map[str(tid)] = t

        for tid in track_ids:
            track = id_map.get(str(tid))
            if track:
                if hasattr(playlist, "add"):
                    playlist.add(track)
                else:
                    playlist.add_track(track)
        if hasattr(db, "add"):
            db.add(playlist)
        else:
            db.add_playlist(playlist)
        db.copy_delayed_files()
    except GpodException as exc:
        logger.error("gpod error creating playlist %s: %s", name, exc)
        raise LibpodError(f"Failed to create playlist {name}: {exc}") from exc
    finally:
        db.close()

