#!/usr/bin/env bash
# Simple installer for ipod-dock dependencies and services
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_USER="ipod"

build_libgpod() {
    echo "Building libgpod from source..."
    sudo apt-get install -y build-essential git libtool intltool gtk-doc-tools \
        autoconf automake \
        libglib2.0-dev libimobiledevice-dev libplist-dev libxml2-dev \
        python3-dev libsqlite3-dev
    workdir=$(mktemp -d)
    git clone --depth 1 https://github.com/fadingred/libgpod "$workdir/libgpod"
    pushd "$workdir/libgpod" >/dev/null
    # Apply patches for newer GLib and compiler warnings
    sed -i 's/g_memdup (/g_memdup2 (/g' src/db-artwork-parser.c
    sed -i 's/^\(GList \*\)artwork_glist = NULL;/GList **artwork_list = NULL;/' src/db-artwork-parser.c
    sed -i '/ctx->db->db_type == DB_TYPE_ITUNES)/,/ctx->artwork =/s/ctx->artwork = &artwork_glist;/artwork_list = g_new0 (GList *, 1);\n            ctx->artwork = artwork_list;/' src/db-artwork-parser.c
    sed -i '/g_list_free (*ctx->artwork);/a\    g_free (ctx->artwork);' src/db-artwork-parser.c
    export AUTOMAKE=automake
    export ACLOCAL=aclocal
    pcdir=$(pkg-config --variable=pcfiledir libplist-2.0 2>/dev/null || true)
    if [ -n "$pcdir" ] && [ ! -e "$pcdir/libplist.pc" ] && [ -e "$pcdir/libplist-2.0.pc" ]; then
        sudo ln -s "$pcdir/libplist-2.0.pc" "$pcdir/libplist.pc"
    fi
    autoreconf -fvi
    CFLAGS="-Wno-error=deprecated-declarations -Wno-error=dangling-pointer" \
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

