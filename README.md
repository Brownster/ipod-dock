# ipod-dock

This project aims to sync an iPod Classic with a Raspberry Pi Zero W so music or podcasts can be uploaded over Wi-Fi.  The repository will contain scripts and a small web API to manage uploads, track listings and integration with an iPod dock.

See [research.md](research.md) for notes on the hardware setup and [roadmap.md](roadmap.md) for planned tasks.

![Screenshot_20250614_170158](https://github.com/user-attachments/assets/f6405a25-d809-4ad6-ba63-4b399a248f20)

## Setup

Install the required system packages (on Raspberry Pi OS):

```bash
sudo apt-get update
sudo apt-get install python3-gpod libgpod-common ffmpeg
```

Create a Python virtual environment in the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

This repository will use the virtual environment for any Python tools and future dependencies.

## Syncing files

During the early development phase queued files can be synced manually using the
`sync_from_queue` module:

```bash
python -m ipod_sync.sync_from_queue --device /dev/sda1
```

Any audio files placed in the `sync_queue/` directory will be imported to the
iPod and removed from the queue.

Log output is written to `logs/ipod_sync.log` and rotated automatically. See
`docs/development.md` for developer notes on the logging configuration.


## Web API

A small FastAPI application exposes upload and track management endpoints. Start
the server for development with:

```bash
python -m ipod_sync.app
```

See [docs/development.md](docs/development.md) for the list of endpoints.
Plugin developers can find usage examples in
[docs/plugin_api.md](docs/plugin_api.md).
