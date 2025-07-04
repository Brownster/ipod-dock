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

A udev rule installs `ipod-mount.service` which mounts the iPod automatically
when it is connected. The helper script detects the first FAT partition and
mounts it at `/opt/ipod-dock/mnt/ipod`.

Start the API server:

```bash
python -m ipod_sync.app
```

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

## Contributing

Run the test suite before submitting patches:

```bash
pytest
```

Formatting follows the standard `black` style. New features should include unit tests when possible.
