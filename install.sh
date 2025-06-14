#!/usr/bin/env bash
# Simple installer for ipod-dock dependencies and services
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_USER="ipod"

# Install system packages
if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3-gpod libgpod-common ffmpeg python3-venv
fi

# Create virtual environment
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv "$PROJECT_DIR/.venv"
fi
source "$PROJECT_DIR/.venv/bin/activate"

# Install Python packages
pip install -U pip fastapi uvicorn watchdog httpx python-multipart

# Ensure dedicated service user exists
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo useradd -r -s /usr/sbin/nologin -d "$PROJECT_DIR" "$SERVICE_USER"
fi

# Install systemd services if available
if command -v systemctl >/dev/null; then
    for svc in ipod-api.service ipod-watcher.service; do
        tmp=$(mktemp)
        sed "s|/path/to/ipod-dock|$PROJECT_DIR|; s|User=.*|User=$SERVICE_USER|" "$PROJECT_DIR/$svc" > "$tmp"
        sudo mv "$tmp" "/etc/systemd/system/$svc"
    done
    sudo systemctl daemon-reload
    sudo systemctl enable ipod-api.service ipod-watcher.service
    echo "Services installed. Start them with:\n  sudo systemctl start ipod-api.service ipod-watcher.service"
fi

