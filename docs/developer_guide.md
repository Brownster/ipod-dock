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

If the `python3-gpod` package is missing, run `../install.sh` which will
compile the libgpod bindings automatically.

## Running the services

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
python -m ipod_sync.sync_from_queue --device /dev/sda1
```

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
