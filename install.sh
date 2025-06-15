#!/usr/bin/env bash
# Simple installer for ipod-dock dependencies and services
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="/opt/ipod-dock"
SERVICE_USER="ipod"

# Ensure the project resides in a path accessible to the service user
if [ "$PROJECT_DIR" != "$TARGET_DIR" ]; then
    echo "Copying project to $TARGET_DIR..."
    sudo mkdir -p "$TARGET_DIR"
    sudo rsync -a --exclude '.venv' "$PROJECT_DIR/" "$TARGET_DIR/"
    PROJECT_DIR="$TARGET_DIR"
fi
cd "$PROJECT_DIR"

build_libgpod() {
    echo "Building libgpod from source..."
    sudo apt-get install -y build-essential git libtool intltool gtk-doc-tools \
        autoconf automake \
        libglib2.0-dev libimobiledevice-dev libplist-dev libxml2-dev \
        python3-dev libsqlite3-dev
    workdir=$(mktemp -d)
    git clone --depth 1 https://github.com/john8675309/libgpod-0.8.3.git "$workdir/libgpod"
    pushd "$workdir/libgpod" >/dev/null
    export AUTOMAKE=automake
    export ACLOCAL=aclocal
    pcdir=$(pkg-config --variable=pcfiledir libplist-2.0 2>/dev/null || true)
    if [ -n "$pcdir" ] && [ ! -e "$pcdir/libplist.pc" ] && [ -e "$pcdir/libplist-2.0.pc" ]; then
        sudo ln -s "$pcdir/libplist-2.0.pc" "$pcdir/libplist.pc"
    fi
    ./configure --with-python=/usr/bin/python3
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
# Create or update the service user
if id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo usermod -d "$PROJECT_DIR" "$SERVICE_USER"
else
    sudo useradd -r -s /usr/sbin/nologin -d "$PROJECT_DIR" "$SERVICE_USER"
fi
# Ensure service user can access the project directory
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$PROJECT_DIR"

# Install systemd services if available
if command -v systemctl >/dev/null; then
    for svc in ipod-api.service ipod-watcher.service; do
        tmp=$(mktemp)
        sed "s|User=.*|User=$SERVICE_USER|" "$PROJECT_DIR/$svc" > "$tmp"
        sudo mv "$tmp" "/etc/systemd/system/$svc"
    done
    sudo systemctl daemon-reload
    sudo systemctl enable ipod-api.service ipod-watcher.service
    echo "Services installed. Start them with:\n  sudo systemctl start ipod-api.service ipod-watcher.service"
fi

