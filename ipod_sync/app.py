"""FastAPI application exposing basic iPod management endpoints."""

from __future__ import annotations

import logging

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from importlib import resources

from . import config
from .auth import verify_api_key
from .logging_setup import setup_logging
from .playback import SerialPlayback
from .api_helpers import (
    save_to_queue,
    get_tracks,
    remove_track,
    list_queue,
    clear_queue,
    get_stats,
    get_playlists,
    create_new_playlist,
    is_ipod_connected,
)
from . import sync_from_queue, podcast_fetcher

logger = logging.getLogger(__name__)

app = FastAPI(title="ipod-dock")
static_dir = resources.files("ipod_sync").joinpath("static")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

auth_dep = Depends(verify_api_key)
playback_controller = SerialPlayback()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve the simple HTML interface."""
    logger.debug("Serving index page")
    page = resources.files("ipod_sync.templates").joinpath("index.html")
    return page.read_text(encoding="utf-8")


@app.get("/audible", response_class=HTMLResponse)
async def audible_page() -> str:
    """Serve the Audible import page."""
    logger.debug("Serving audible page")
    page = resources.files("ipod_sync.templates").joinpath("audible.html")
    return page.read_text(encoding="utf-8")


@app.get("/status", dependencies=[auth_dep])
async def status() -> dict:
    """Return service health information."""
    logger.debug("Status check")
    connected = is_ipod_connected(config.IPOD_DEVICE)
    return {"status": "ok", "connected": connected}


@app.post("/upload", dependencies=[auth_dep])
async def upload(file: UploadFile = File(...)) -> dict:
    """Accept a file upload and place it in the sync queue."""
    data = await file.read()
    path = save_to_queue(file.filename, data)
    return {"queued": path.name}


@app.post("/upload/{category}", dependencies=[auth_dep])
async def upload_category(category: str, file: UploadFile = File(...)) -> dict:
    """Upload a file to a specific category such as ``music`` or ``audiobook``."""
    if category not in {"music", "audiobook", "podcast"}:
        raise HTTPException(400, "invalid category")
    data = await file.read()
    path = save_to_queue(file.filename, data, category=category)
    return {"queued": path.name, "category": category}


@app.get("/tracks", dependencies=[auth_dep])
async def tracks() -> list[dict]:
    """Return the list of tracks currently on the iPod."""
    try:
        return get_tracks(config.IPOD_DEVICE)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error("Failed to list tracks: %s", exc)
        raise HTTPException(500, str(exc))


@app.delete("/tracks/{track_id}", dependencies=[auth_dep])
async def delete_track(track_id: str) -> dict:
    """Remove a track from the iPod."""
    try:
        remove_track(track_id, config.IPOD_DEVICE)
    except KeyError:
        raise HTTPException(404, "Track not found")
    except Exception as exc:  # pragma: no cover - unexpected failures
        logger.error("Failed to delete track %s: %s", track_id, exc)
        raise HTTPException(500, str(exc))
    return {"deleted": track_id}


@app.get("/playlists", dependencies=[auth_dep])
async def playlists() -> list[dict]:
    """Return playlists and their track IDs."""
    try:
        return get_playlists(config.IPOD_DEVICE)
    except Exception as exc:  # pragma: no cover - unexpected failures
        logger.error("Failed to list playlists: %s", exc)
        raise HTTPException(500, str(exc))


@app.post("/playlists", dependencies=[auth_dep])
async def playlists_create(payload: dict) -> dict:
    """Create a new playlist from selected track IDs."""
    name = payload.get("name")
    tracks = payload.get("tracks", [])
    if not name:
        raise HTTPException(400, "name required")
    try:
        create_new_playlist(name, [str(t) for t in tracks], config.IPOD_DEVICE)
    except Exception as exc:  # pragma: no cover - unexpected failures
        logger.error("Failed to create playlist %s: %s", name, exc)
        raise HTTPException(500, str(exc))
    return {"created": name}


@app.get("/queue", dependencies=[auth_dep])
async def queue() -> list[dict]:
    """Return the list of files waiting in the sync queue."""
    return list_queue()


@app.post("/queue/clear", dependencies=[auth_dep])
async def queue_clear() -> dict:
    """Remove all files from the sync queue."""
    clear_queue()
    return {"cleared": True}


@app.post("/sync", dependencies=[auth_dep])
async def sync() -> dict:
    """Trigger a sync of queued files."""
    try:
        sync_from_queue.sync_queue(config.IPOD_DEVICE)
    except Exception as exc:  # pragma: no cover - runtime failures
        logger.error("Sync failed: %s", exc)
        raise HTTPException(500, str(exc))
    return {"synced": True}


@app.get("/stats", dependencies=[auth_dep])
async def stats() -> dict:
    """Return high level statistics for the dashboard."""
    return get_stats(config.IPOD_DEVICE)


@app.post("/podcasts/fetch", dependencies=[auth_dep])
async def podcasts_fetch(payload: dict) -> dict:
    """Download episodes from an RSS feed into the queue."""
    feed_url = payload.get("feed_url")
    if not feed_url:
        raise HTTPException(400, "feed_url required")
    try:
        downloaded = podcast_fetcher.fetch_podcasts(feed_url)
    except Exception as exc:  # pragma: no cover - unexpected failures
        logger.error("Failed to fetch podcasts: %s", exc)
        raise HTTPException(500, str(exc))
    return {"downloaded": [p.name for p in downloaded]}


@app.post("/control/{cmd}", dependencies=[auth_dep])
async def control(cmd: str) -> dict:
    try:
        if cmd == "play":
            playback_controller.play_pause()
        elif cmd == "pause":
            playback_controller.play_pause()
        elif cmd == "next":
            playback_controller.next_track()
        elif cmd == "prev":
            playback_controller.prev_track()
        else:
            raise HTTPException(400, "invalid command")
    except HTTPException as exc:
        raise exc
    except Exception as exc:  # pragma: no cover - runtime errors
        logger.error("Playback command %s failed: %s", cmd, exc)
        raise HTTPException(500, str(exc))
    return {"status": "ok"}


def main() -> None:
    """Run a development server if executed as a script."""
    import uvicorn

    setup_logging()
    uvicorn.run("ipod_sync.app:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
