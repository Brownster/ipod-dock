Phase 1 – MVP: Manual Upload & Sync
#	Task	
1.1	Set up development repo – create ipod_sync repo, add README, .gitignore, and issue template. ☑
1.2     Install prerequisites – sudo apt install python3-gpod libgpod-common ffmpeg (Pi OS) + create a venv.    ☑
1.3	Create project skeleton – folders: ipod_sync/, sync_queue/, uploads/, plus app.py, libpod_wrapper.py, config.py, utils.py.	☑
1.4     Implement mount helpers (utils.py) – mount_ipod(), eject_ipod(), using subprocess to call mount/umount/eject.   ☑
1.5     Write libgpod wrapper (libpod_wrapper.py) – functions: add_track(filepath), delete_track(db_id), list_tracks(). ☑
1.6     Implement simple sync script (sync_from_queue.py) – watches sync_queue/, mounts iPod, calls add_track(), ejects.        ☑
1.7	Add logging – log to logs/ipod_sync.log with rotation.	☑
1.8	Test end-to-end – copy an MP3 to sync_queue/, run script, verify track appears on iPod after eject.	☐
Phase 2 – Basic API & Web UI
#	Task	
2.1	Add Flask/FastAPI – scaffold app.py with /status (health) endpoint.	☐
2.2	POST /upload endpoint – accept file upload, save to sync_queue/, return JSON.	☐
2.3	GET /tracks endpoint – return JSON list from list_tracks().	☐
2.4	DELETE /tracks/<id> endpoint – remove a track, re-write DB, eject.	☐
2.5	Add simple HTML UI – use Bootstrap/Tailwind, fetch /tracks, show table, upload form.	☐
2.6	Systemd service – create unit file for API + sync watcher so they start on boot.	☐
Phase 3 – Dock Detection & Playback Control
#	Task	
3.1	Choose dock-detect method – GPIO reed switch or USB hotplug hook; document wiring.	☐
3.2	Add udev rule / GPIO listener – triggers sync on dock, eject on undock.	☐
3.3	Serial wiring for AAP – connect dock pins 12/13 to Pi UART; verify 19 200 baud echo.	☐
3.4	Implement play/pause API – Python class for AAP commands (play, pause, next, prev).	☐
3.5	Expose /control/<cmd> endpoint – call AAP methods; add buttons in Web UI.	☐
3.6	External speaker hookup – wire dock line-out to small amp/speaker; verify audio.	☐
Phase 4 – AudioBookShelf Integration & Automation
#	Task	
4.1	Design ABS plugin spec – decide REST payload (/upload), auth token, metadata JSON.	☐
4.2	Write ABS plugin – in JavaScript/TypeScript; add “Send to iPod” button in ABS UI.	☐
4.3	Implement queue watcher daemon – in watcher.py, uses inotify to auto-sync new arrivals.	☐
4.4	On-the-fly conversion – integrate ffmpeg; convert non-MP3/AAC inputs; unit tests.	☐
4.5	Daily cleanup cron – prune old sync logs, remove temp files.	☐
4.6	OTA update script – self-update via git pull && systemctl restart ipod_sync.	☐

Actionable tweaks to the roadmap

    Update Task 1.6 – after add_track() returns success, delete the original file (and any /tmp work-file).

    Logging – record filename, bytes copied, and “deleted OK” so you can audit space usage.

    Config option – add KEEP_LOCAL_COPY = False in config.py. Later, if you enable a mirror cache, flip it to True.

Phase 5 – Polishing & Stretch Goals
#	Task	
5.1	User auth for Web UI & API – JWT or basic auth.	☐
5.2	Progress notifications – websocket or SSE to show sync status live.	☐
5.3	Battery / charge display – parse AAP status, expose on UI.	☐
5.4	Multi-device support – handle more than one iPod by serial number in /dev/disk/by-id/.	☐
5.5	Rockbox detection – optional path if user installs Rockbox, switch to plain USB copy + playlist file.	☐
