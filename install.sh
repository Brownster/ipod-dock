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
    echo "Building libgpod from source with sgutils support..."
    sudo apt-get install -y build-essential git meson ninja-build \
        swig libtool intltool gtk-doc-tools \
        libglib2.0-dev libimobiledevice-dev libplist-dev libxml2-dev \
        libgdk-pixbuf2.0-dev python3-dev libsqlite3-dev \
        python-gi-dev python3-mutagen libsgutils2-dev sg3-utils

    # Debian packages the SCSI utils library as libsgutils2.so but
    # the libgpod build looks for libsgutils.so. Create a symlink if
    # needed so Meson can locate the library.
    sgutils_path=$(ldconfig -p | awk '/libsgutils2\.so/ {print $NF; exit}')
    if [ -n "$sgutils_path" ]; then
        sgutils_dir=$(dirname "$sgutils_path")
        if [ ! -e "$sgutils_dir/libsgutils.so" ]; then
            echo "Creating libsgutils.so symlink in $sgutils_dir"
            sudo ln -s "$(basename "$sgutils_path")" "$sgutils_dir/libsgutils.so"
        fi
    fi

    workdir=$(mktemp -d)
    git clone --depth 1 https://github.com/Brownster/libgpod.git "$workdir/libgpod"
    pushd "$workdir/libgpod" >/dev/null
    
    # Configure with sgutils support explicitly enabled
    meson setup build --prefix=/usr -Dsgutils=enabled
    ninja -C build
    sudo ninja -C build install
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
pip install audible-cli mutagen

# Ensure dedicated service user exists
# Create or update the service user
if id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo usermod -d "$PROJECT_DIR" "$SERVICE_USER"
else
    sudo useradd -r -s /usr/sbin/nologin -d "$PROJECT_DIR" "$SERVICE_USER"
fi
# Ensure service user can access the project directory
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$PROJECT_DIR"

# Fix gpod Python bindings path issue
if [ -d "/usr/usr/lib/python3/dist-packages/gpod" ]; then
    echo "Fixing gpod Python bindings path..."
    sudo ln -sf /usr/usr/lib/python3/dist-packages/gpod /usr/lib/python3/dist-packages/gpod
fi

# Create gpod symlink in virtual environment
if [ -d "/usr/lib/python3/dist-packages/gpod" ] && [ -d "$PROJECT_DIR/.venv/lib/python3.11/site-packages" ]; then
    echo "Creating gpod symlink in virtual environment..."
    sudo -u "$SERVICE_USER" ln -sf /usr/lib/python3/dist-packages/gpod "$PROJECT_DIR/.venv/lib/python3.11/site-packages/gpod"
fi

# Ensure the iPod mount point exists and is writable by the service user
MOUNT_POINT="$TARGET_DIR/mnt/ipod"
sudo mkdir -p "$MOUNT_POINT"
sudo chown "$SERVICE_USER":"$SERVICE_USER" "$MOUNT_POINT"

# Create mount helper script with proper ownership for iPod mounting
MOUNT_HELPER="/usr/local/bin/mount-ipod"
if [ ! -f "$MOUNT_HELPER" ]; then
    echo "Creating mount helper script at $MOUNT_HELPER"
    sudo tee "$MOUNT_HELPER" << 'EOF' >/dev/null
#!/bin/bash
# Helper script to mount iPod with correct permissions
SERVICE_USER_ID=$(id -u ipod)
SERVICE_GROUP_ID=$(id -g ipod)
/bin/mount -t vfat -o "uid=${SERVICE_USER_ID},gid=${SERVICE_GROUP_ID}" -- "$1" /opt/ipod-dock/mnt/ipod
EOF
    sudo chmod 755 "$MOUNT_HELPER"
fi

# Allow the service account to mount and unmount without a password
SUDOERS_FILE="/etc/sudoers.d/ipod-dock"
SUDO_RULE="${SERVICE_USER} ALL=(root) NOPASSWD: \\
    /usr/local/bin/mount-ipod \*, \\
    /bin/mount -t vfat -- \* ${MOUNT_POINT}, \\
    /bin/mount -t vfat \* ${MOUNT_POINT}, \\
    /bin/umount ${MOUNT_POINT}, \\
    /usr/bin/eject ${MOUNT_POINT}, \\
    /usr/bin/ipod-read-sysinfo-extended \* ${MOUNT_POINT}"
if [ ! -f "$SUDOERS_FILE" ]; then
    echo "Adding sudoers rule for $SERVICE_USER at $SUDOERS_FILE"
    echo "$SUDO_RULE" | sudo tee "$SUDOERS_FILE" >/dev/null
    sudo chmod 0440 "$SUDOERS_FILE"
fi

# Install systemd services if available
if command -v systemctl >/dev/null; then
    for svc in ipod-api.service ipod-watcher.service ipod-listener.service; do
        tmp=$(mktemp)
        sed "s|User=.*|User=$SERVICE_USER|" "$PROJECT_DIR/$svc" > "$tmp" 2>/dev/null || cp "$PROJECT_DIR/$svc" "$tmp"
        sudo mv "$tmp" "/etc/systemd/system/$svc"
    done
    sudo systemctl daemon-reload
    sudo systemctl enable ipod-api.service ipod-watcher.service ipod-listener.service
    echo "Services installed. Start them with:\n  sudo systemctl start ipod-api.service ipod-watcher.service ipod-listener.service"
fi

# Test the installation
echo "Testing installation..."
if [ -d "$PROJECT_DIR/.venv" ]; then
    echo "✓ Virtual environment created"
else
    echo "✗ Virtual environment missing"
fi

if [ -f "$SUDOERS_FILE" ]; then
    echo "✓ Sudoers rule installed"
else
    echo "✗ Sudoers rule missing"
fi

if [ -d "$PROJECT_DIR/.venv/lib/python3.11/site-packages/gpod" ]; then
    echo "✓ gpod Python bindings linked"
else
    echo "✗ gpod Python bindings not linked"
fi

if id "$SERVICE_USER" >/dev/null 2>&1; then
    echo "✓ Service user '$SERVICE_USER' exists"
else
    echo "✗ Service user '$SERVICE_USER' missing"
fi

echo "Installation complete!"
echo "To start services: sudo systemctl start ipod-api.service ipod-watcher.service ipod-listener.service"
echo "Web UI will be available at: http://$(hostname -I | awk '{print $1}'):8000"

