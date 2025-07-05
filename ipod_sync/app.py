"""FastAPI application exposing basic iPod management endpoints."""

from __future__ import annotations

import logging
import subprocess

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
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
from . import sync_from_queue, podcast_fetcher, audible_import
from .plugins.manager import plugin_manager
from .routers import plugins as plugins_router

AUDIBLE_PLUGIN_ID = "audible"

from . import youtube_downloader

logger = logging.getLogger(__name__)

app = FastAPI(title="ipod-dock")

@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the plugin manager."""
    plugin_manager.discover_plugins()

app.include_router(plugins_router.router)
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


@app.get("/api/auth/status")
async def auth_status() -> dict:
    """Return whether the Audible plugin is authenticated."""
    plugin = plugin_manager.get_plugin(AUDIBLE_PLUGIN_ID)
    return {"authenticated": plugin.is_authenticated()}


@app.get("/api/library")
async def audible_library() -> list[dict]:
    """Return the user's Audible library via the plugin."""
    plugin = plugin_manager.get_plugin(AUDIBLE_PLUGIN_ID)
    if not plugin.is_authenticated():
        raise HTTPException(401, "Not authenticated")
    try:
        items = plugin.fetch_library()
        return [
            {
                "title": item.title,
                "artist": item.artist,
                "album": item.album,
                "duration": item.duration,
                "category": item.category,
                "metadata": item.metadata or {},
            }
            for item in items
        ]
    except Exception as exc:
        logger.error("Failed to fetch library: %s", exc)
        raise HTTPException(500, "Failed to fetch library")


@app.post("/api/convert")
async def audible_convert(payload: dict) -> dict:
    asin = payload.get("asin")
    title = payload.get("title")
    if not asin or not title:
        raise HTTPException(400, "asin and title required")

    plugin = plugin_manager.get_plugin(AUDIBLE_PLUGIN_ID)
    if not plugin.is_authenticated():
        raise HTTPException(401, "Not authenticated")

    try:
        file_path = plugin.download_item(
            asin, {"asin": asin, "title": title}
        )
        return {"file": Path(file_path).name}
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        raise HTTPException(500, "Download failed")


@app.get("/api/status")
async def audible_status() -> dict:
    return audible_import.JOBS


@app.get("/downloads/{filename}")
async def audible_download(filename: str):
    path = (config.SYNC_QUEUE_DIR / "audiobook") / filename
    if not path.exists():
        raise HTTPException(404, "file not found")
    return FileResponse(
        str(path), filename=filename, media_type="application/octet-stream"
    )


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


@app.post("/youtube", dependencies=[auth_dep])
async def youtube_download(payload: dict) -> dict:
    url = payload.get("url")
    category = payload.get("category", "music")
    if not url:
        raise HTTPException(400, "url required")
    if category not in {"music", "audiobook", "podcast"}:
        raise HTTPException(400, "invalid category")
    try:
        path = youtube_downloader.download_audio(url, category)
    except Exception as exc:
        logger.error("YouTube download failed: %s", exc)
        raise HTTPException(500, str(exc))
    return {"queued": path.name, "category": category}


@app.post("/youtube/{category}", dependencies=[auth_dep])
async def youtube_download_category(category: str, payload: dict) -> dict:
    url = payload.get("url")
    if not url:
        raise HTTPException(400, "url required")
    if category not in {"music", "audiobook", "podcast"}:
        raise HTTPException(400, "invalid category")
    try:
        path = youtube_downloader.download_audio(url, category)
    except Exception as exc:
        logger.error("YouTube download failed: %s", exc)
        raise HTTPException(500, str(exc))
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
    import os
    import sys
    import uvicorn

    setup_logging()

    interactive = sys.stdin.isatty()
    skip_auth = os.environ.get("IPOD_SKIP_AUDIBLE_AUTH") == "1" or not interactive

    print("=" * 60)
    print("Checking Audible Authentication Status...")
    authenticated = audible_import.check_authentication()

    if skip_auth:
        if not authenticated:
            logger.warning("Audible authentication not detected; starting anyway")
    while not authenticated and not skip_auth:
        print("\n[!] Audible authentication is required.")
        print("    Please follow the prompts from 'audible-cli' to log in.")
        print("    This will likely open a browser window.")
        choice = input(
            "    Press ENTER to start authentication, or type 'q' to quit: "
        ).lower()
        if choice == "q":
            print("Exiting.")
            return
        subprocess.run(["audible", "quickstart"])
        print("\nChecking authentication status again...")
        authenticated = audible_import.check_authentication()
        if not authenticated:
            print("[!] Authentication still not detected. Please try again.")
    if authenticated:
        print("\n[\u2713] Audible is authenticated.")
    print("=" * 60)
    uvicorn.run("ipod_sync.app:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()

