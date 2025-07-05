"""FastAPI application with modular router structure."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from importlib import resources

from .routers import tracks, playlists, queue, plugins, control, config as config_router
from .plugins.manager import plugin_manager
from .logging_setup import setup_logging
from . import config

# Re-export commonly used helpers for backward compatibility
from .api_helpers import (
    is_ipod_connected,
    save_to_queue,
    list_queue,
    clear_queue,
    get_tracks,
    remove_track,
    get_playlists,
    create_new_playlist,
    get_stats,
)
from . import sync_from_queue
from .routers.control import playback_controller

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting ipod-dock API v2.0")

    # Initialize plugin system
    plugin_manager.discover_plugins()
    logger.info(f"Discovered {len(plugin_manager._plugin_classes)} plugins")

    # Validate configuration
    try:
        from .config.manager import config_manager
        config_manager._validate_configuration()
        logger.info("Configuration validation passed")
    except Exception as e:  # pragma: no cover - configuration errors
        logger.error(f"Configuration validation failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down ipod-dock API")


app = FastAPI(
    title="iPod Dock API",
    description="Advanced iPod management and media syncing API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.config_manager.config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = resources.files("ipod_sync").joinpath("static")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include all routers
app.include_router(tracks.router)
app.include_router(playlists.router)
app.include_router(queue.router)
app.include_router(plugins.router)
app.include_router(control.router)
app.include_router(config_router.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception in {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url.path),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve the main dashboard."""
    page = resources.files("ipod_sync.templates").joinpath("index.html")
    return page.read_text(encoding="utf-8")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# Legacy endpoint for backward compatibility
from .auth import verify_api_key


@app.get("/status")
async def legacy_status(_: None = Depends(verify_api_key)):
    """Legacy status endpoint - redirects to new API."""
    connected = is_ipod_connected(config.IPOD_DEVICE)
    return {
        "status": "ok",
        "connected": connected,
        "message": "This endpoint is deprecated. Use /api/v1/control/status instead.",
    }


def main() -> None:
    """Run development server."""
    import uvicorn

    setup_logging()
    logger.info("Starting development server")

    uvicorn.run(
        "ipod_sync.app:app",
        host=config.config_manager.config.server.host,
        port=config.config_manager.config.server.port,
        log_level="info",
        reload=True,
    )


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()

