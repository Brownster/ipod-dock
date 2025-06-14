"""FastAPI application exposing basic iPod management endpoints."""

from __future__ import annotations

import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from importlib import resources

from . import config
from .logging_setup import setup_logging
from .api_helpers import (
    save_to_queue,
    get_tracks,
    remove_track,
    list_queue,
    clear_queue,
    get_stats,
)
from . import sync_from_queue

logger = logging.getLogger(__name__)

app = FastAPI(title="ipod-dock")
static_dir = resources.files("ipod_sync").joinpath("static")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve the simple HTML interface."""
    logger.debug("Serving index page")
    page = resources.files("ipod_sync.templates").joinpath("index.html")
    return page.read_text(encoding="utf-8")


@app.get("/status")
async def status() -> dict:
    """Return service health information."""
    logger.debug("Status check")
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """Accept a file upload and place it in the sync queue."""
    data = await file.read()
    path = save_to_queue(file.filename, data)
    return {"queued": path.name}


@app.post("/upload/{category}")
async def upload_category(category: str, file: UploadFile = File(...)) -> dict:
    """Upload a file to a specific category such as ``music`` or ``audiobook``."""
    if category not in {"music", "audiobook"}:
        raise HTTPException(400, "invalid category")
    data = await file.read()
    path = save_to_queue(file.filename, data, category=category)
    return {"queued": path.name, "category": category}


@app.get("/tracks")
async def tracks() -> list[dict]:
    """Return the list of tracks currently on the iPod."""
    try:
        return get_tracks(config.IPOD_DEVICE)
    except Exception as exc:
        logger.error("Failed to list tracks: %s", exc)
        raise HTTPException(500, str(exc))


@app.delete("/tracks/{track_id}")
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


@app.get("/queue")
async def queue() -> list[dict]:
    """Return the list of files waiting in the sync queue."""
    return list_queue()


@app.post("/queue/clear")
async def queue_clear() -> dict:
    """Remove all files from the sync queue."""
    clear_queue()
    return {"cleared": True}


@app.post("/sync")
async def sync() -> dict:
    """Trigger a sync of queued files."""
    sync_from_queue.sync_queue(config.IPOD_DEVICE)
    return {"synced": True}


@app.get("/stats")
async def stats() -> dict:
    """Return high level statistics for the dashboard."""
    return get_stats(config.IPOD_DEVICE)


def main() -> None:
    """Run a development server if executed as a script."""
    import uvicorn

    setup_logging()
    uvicorn.run("ipod_sync.app:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
