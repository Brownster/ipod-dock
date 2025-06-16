#!/usr/bin/env bash
# Update installed ipod-dock using the files from the current repository.
# Run this script from the project clone used during installation (e.g. ~/ipod-dock).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="/opt/ipod-dock"
SERVICE_USER="ipod"

# Fetch the latest version of the repository
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Updating source repository in $PROJECT_DIR..."
    git pull --ff-only
fi

echo "Syncing files to $TARGET_DIR..."
sudo mkdir -p "$TARGET_DIR"
# Exclude runtime data and local virtualenv
sudo rsync -a --exclude '.venv' --exclude 'logs' --exclude 'uploads' --exclude 'sync_queue' \
    "$PROJECT_DIR/" "$TARGET_DIR/"

# Create or update the virtual environment
if [ ! -d "$TARGET_DIR/.venv" ]; then
    python3 -m venv "$TARGET_DIR/.venv"
fi

sudo -u "$SERVICE_USER" "$TARGET_DIR/.venv/bin/pip" install -U pip
sudo -u "$SERVICE_USER" "$TARGET_DIR/.venv/bin/pip" install -r "$TARGET_DIR/requirements.txt"

# Ensure the service user exists
if id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo usermod -d "$TARGET_DIR" "$SERVICE_USER"
else
    sudo useradd -r -s /usr/sbin/nologin -d "$TARGET_DIR" "$SERVICE_USER"
fi
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$TARGET_DIR"

# Ensure mount permissions are configured for the service user
IPOD_DEVICE="/dev/sda1"
MOUNT_POINT="$TARGET_DIR/mnt/ipod"
sudo mkdir -p "$MOUNT_POINT"
sudo chown "$SERVICE_USER":"$SERVICE_USER" "$MOUNT_POINT"
if ! grep -qs "${MOUNT_POINT}" /etc/fstab; then
    echo "Adding $IPOD_DEVICE mount entry to /etc/fstab..."
    echo "$IPOD_DEVICE $MOUNT_POINT vfat noauto,user,uid=$SERVICE_USER,gid=$SERVICE_USER 0 0" | sudo tee -a /etc/fstab
fi

# Refresh systemd units and restart services
if command -v systemctl >/dev/null; then
    for svc in ipod-api.service ipod-watcher.service; do
        tmp=$(mktemp)
        sed "s|User=.*|User=$SERVICE_USER|" "$PROJECT_DIR/$svc" > "$tmp"
        sudo mv "$tmp" "/etc/systemd/system/$svc"
    done
    sudo systemctl daemon-reload
    sudo systemctl restart ipod-api.service ipod-watcher.service
fi

echo "Update complete."
