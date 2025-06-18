#!/bin/bash
# Mount the iPod data partition when triggered by udev.

set -euo pipefail

MOUNT_POINT="/opt/ipod-dock/mnt/ipod"
MOUNT_USER="ipod"

# Resolve UID/GID for mount options
UID_NUM=$(id -u "$MOUNT_USER" 2>/dev/null || echo 1000)
GID_NUM=$(id -g "$MOUNT_USER" 2>/dev/null || echo 1000)

# Detect the first FAT/VFAT partition of any connected drive
PARTITION=$(lsblk -lno NAME,FSTYPE | awk '$2 ~ /^vfat$/ {print "/dev/"$1; exit}')

if [ -z "$PARTITION" ]; then
    exit 0
fi

# Skip if already mounted
if mountpoint -q "$MOUNT_POINT"; then
    exit 0
fi

mkdir -p "$MOUNT_POINT"
mount -t vfat \
    -o uid="$UID_NUM",gid="$GID_NUM",umask=000,nosuid,nodev,noatime \
    "$PARTITION" "$MOUNT_POINT"

