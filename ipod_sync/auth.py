from __future__ import annotations

import os

from fastapi import Header, HTTPException

from .config import config_manager


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Validate the ``X-API-Key`` header against :data:`~ipod_sync.config.API_KEY`."""
    key = config_manager.config.server.api_key
    if key is None:
        return
    if x_api_key != key:
        raise HTTPException(status_code=401, detail="invalid api key")
