"""Wrapper functions for interacting with libgpod."""

from pathlib import Path


def add_track(filepath: Path) -> None:
    """Add a track at *filepath* to the iPod library."""
    raise NotImplementedError("add_track() not yet implemented")


def delete_track(db_id: str) -> None:
    """Delete a track from the iPod by its database ID."""
    raise NotImplementedError("delete_track() not yet implemented")


def list_tracks():
    """Return a list of tracks currently on the iPod."""
    raise NotImplementedError("list_tracks() not yet implemented")

