# Updated Roadmap

This document reflects the actual features present in the repository as of June 2025 and outlines what remains to be implemented.

## Phase 1 – MVP: Manual Upload & Sync

- [x] Set up development repo and initial skeleton (`ipod_sync/`, `sync_queue/`, etc.)
- [x] Install prerequisites (`python3-gpod`, `ffmpeg`, virtualenv)
- [x] Basic sync script (`sync_from_queue.py`) with logging
- [x] Mount helpers and libgpod wrapper
- [x] Initial end-to-end test copying a file into `sync_queue/`

## Phase 2 – Basic API & Web UI

- [x] FastAPI application exposing `/status`, `/upload`, `/tracks`, etc.
- [x] HTML dashboard served from the API
- [x] Systemd service units (`ipod-api.service`, `ipod-watcher.service`)

## Phase 3 – Dock Detection & Playback Control

The following items have **not** been implemented:

- [ ] Dock detection (udev rule or GPIO listener)
- [ ] Serial wiring for Apple Accessory Protocol (AAP)
- [ ] Playback control API and `/control/<cmd>` endpoint
- [ ] External speaker hookup

## Phase 4 – AudioBookShelf Integration & Automation

Only the queue watcher daemon exists. The rest of the automation features remain TODO:

- [x] Queue watcher daemon (`watcher.py`)
- [ ] AudioBookShelf plugin and REST spec
- [ ] On-the-fly conversion of uploads using `ffmpeg`
- [ ] Daily cleanup job
- [ ] OTA update script

## Phase 5 – Polishing & Stretch Goals

These features are not yet present:

- [ ] Authentication for Web UI/API
- [ ] Progress notifications (websocket/SSE)
- [ ] Battery or charge display via AAP
- [ ] Multi-device support
- [ ] Rockbox detection and alternate sync mode

---

This roadmap replaces the older checklist and matches the current repository state. Future work should focus on Phase 3 and Phase 4 items.
