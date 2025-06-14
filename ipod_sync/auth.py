from __future__ import annotations

import os

from fastapi import Header, HTTPException

from . import config


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Validate the ``X-API-Key`` header against :data:`~ipod_sync.config.API_KEY`."""
    key = config.API_KEY
    if key is None:
        return
    if x_api_key != key:
        raise HTTPException(status_code=401, detail="invalid api key")
