# Developer Guide

This guide summarises the repository layout and common tasks for working on **ipod-dock**.

## Repository layout

- `ipod_sync/` – core package containing the FastAPI server, sync helpers and utilities.
- `tests/` – unit tests using `pytest`.
- `docs/` – documentation including this guide.
- `sync_queue/` – drop files here for the sync script.
- `install.sh` – installs system dependencies and service units.

## Development environment

Create a virtual environment and install the Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

System packages for the iPod bindings and `ffmpeg` can be installed on Debian based systems with:

```bash
sudo apt-get install libgpod-common ffmpeg
```

If the `python3-gpod` package is missing, run `../install.sh` to build the
libgpod bindings from the [`Brownster/libgpod`](https://github.com/Brownster/libgpod)
fork with Python 3 support. The build uses Meson and requires the SQLite
development headers (`libsqlite3-dev`), the libxml2 development package
(`libxml2-dev`), the PyGObject development files (`python-gi-dev`) and the
`python3-mutagen` module.

## Running the services

`ipod-listener.service` monitors USB events and mounts the iPod automatically
when it is connected. The listener detects the first FAT partition and mounts it
at `/opt/ipod-dock/mnt/ipod`.

Start the API server:

```bash
python -m ipod_sync.app
```

All REST endpoints are versioned under `/api/v1/`. When adding new routes use
this prefix so clients can rely on a stable base URL.

Launch the queue watcher (optional, triggers a sync when files appear):

```bash
python -m ipod_sync.watcher
```

You can also run a manual sync at any time:

```bash
python -m ipod_sync.sync_from_queue
```
Add ``--device /dev/sdX2`` if you need to override the detected partition.

Set environment variables to override defaults:

- `IPOD_DEVICE` – block device path of the iPod.
- `IPOD_API_KEY` – secret required by the API.
- `IPOD_SERIAL_PORT` – serial port for playback control.

Log files are written to `logs/ipod_sync.log` by default.

## Plugin system

Media source plugins live under `ipod_sync/plugins` and subclass
`MediaSourcePlugin`. The global `plugin_manager` discovers and loads these
plugins at runtime so new sources can be added without changing the core
application.

## Repository pattern

Data access is encapsulated by repositories in `ipod_sync/repositories`. Use
`RepositoryFactory.get_repository()` to obtain an implementation for the iPod,
sync queue or local library. Repositories emit events when tracks or playlists
change.

## Event bus

The `ipod_sync.events` module provides a simple event bus. Emit events using
helpers such as `emit_sync_started()` and register listeners with
`event_bus.on(EventType, handler)`.

## Configuration manager

`ConfigManager` loads `config/config.json` and optional profile files, applies
environment variable overrides and validates the result. Call
`reload_configuration()` to refresh settings at runtime.

## API routers

The FastAPI server is split into router modules under `ipod_sync/routers` for
tracks, playlists, queue management, plugins and configuration. All routes are
mounted under `/api/v1/` by `app.py`.

## Contributing

Run the test suite before submitting patches:

```bash
pytest
```

Formatting follows the standard `black` style. New features should include unit tests when possible.
