#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from ipod_sync.app import app
import ipod_sync.app as app_module

client = TestClient(app)
app_module.config_manager.config.server.api_key = "secret"
response = client.get("/api/v1/tracks", headers={"X-API-Key": "secret"})
print("Status:", response.status_code)
print("Response:", response.text)