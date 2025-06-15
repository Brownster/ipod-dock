#!/usr/bin/env bash
# Simple installer for ipod-dock dependencies and services
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_USER="ipod"

build_libgpod() {
    echo "Building libgpod from source..."
    sudo apt-get install -y build-essential git libtool intltool \
        autoconf automake \
        libglib2.0-dev libimobiledevice-dev libplist-dev python3-dev
    workdir=$(mktemp -d)
    git clone --depth 1 https://github.com/fadingred/libgpod "$workdir/libgpod"
    pushd "$workdir/libgpod" >/dev/null
    export AUTOMAKE=automake
    ./autogen.sh
    ./configure --with-python3
    make
    sudo make install
    sudo ldconfig
    popd >/dev/null
    rm -rf "$workdir"
}

# Install system packages
if command -v apt-get >/dev/null; then
    sudo apt-get update
    if ! sudo apt-get install -y python3-gpod libgpod-common ffmpeg python3-venv; then
        echo "python3-gpod not available, building from source" >&2
        sudo apt-get install -y libgpod-common ffmpeg python3-venv
        build_libgpod
    fi
fi

# Create virtual environment
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv "$PROJECT_DIR/.venv"
fi
source "$PROJECT_DIR/.venv/bin/activate"

# Install Python packages
pip install -U pip
pip install -r "$PROJECT_DIR/requirements.txt"

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

