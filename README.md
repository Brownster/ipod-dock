# ipod-dock

**WIP** This project aims to sync an iPod Classic with a Raspberry Pi Zero 2 W so music, podcasts and audiobooks can be uploaded over Wi-Fi.  The repository contains scripts and a web API to manage uploads, track listings and integration with an iPod dock.
The Pi Zero 2 W keeps the build compact and power efficient. If you prefer a bit
more CPU power or the convenience of a full-size USB port, a Pi 3A+ is a good
alternative.


See [research.md](research.md) for notes on the hardware setup and [wiring instructions](docs/wiring.md) and [roadmap_v2.md](roadmap_v2.md) for planned tasks.

![Screenshot_20250614_170158](https://github.com/user-attachments/assets/f6405a25-d809-4ad6-ba63-4b399a248f20)

## Features

- **Queue based syncing** – drop files into `sync_queue/` and they are copied to
  the iPod on the next sync run.
- **Automatic conversion** – unsupported formats are converted to MP3 with
  `ffmpeg` before import.
- **Audible integration** – convert books from your Audible library to M4B and
  queue them for syncing.
- **FastAPI web API** providing upload, track management and statistics
  endpoints.
- **Connection status indicator** via the `/status` endpoint to show whether the
  iPod is connected. A file named `ipod_connected` is created in the project root
  when the iPod is mounted and removed on eject; the UI uses this to display the
  current connection state.
- **HTML dashboard** served by the API for manual uploads and browsing the
  library.
- **Watcher daemon** using `watchdog` to trigger syncing when new files appear in
  the queue.
- **USB listener** using `pyudev` to start syncing automatically when the iPod
  is connected.
- **Serial playback control** via the Apple Accessory Protocol for play/pause and
  track skipping.
- **Rotating log files** stored under `logs/` for easy debugging.
- **Systemd service units** so the API and watcher start automatically on boot.

## Dock wiring

The iPod's 30-pin connector carries USB and serial lines that can be wired
directly to the Pi. For a basic connection:

* **USB data** – connect pin 27 (D+) to the Pi's USB D+ and pin 25 (D-) to USB
  D-. Wire pin 23 to the Pi's 5 V supply and pin 16 (or 15) to ground so the Pi
  recognises the iPod as a normal USB device.
* **Serial (optional)** – connect pin 12 (TX) and pin 13 (RX) to the Pi's UART
  (GPIO14/15). Place a ~6.8 kΩ resistor between pin 21 and ground to enable
  accessory mode for playback control.
* **Audio** – pin 4 provides left line out, pin 3 right, with pin 2 as ground if
  you want to feed speakers or an amplifier.

See [docs/wiring.md](docs/wiring.md) for the full pin list.

## Setup

To run this (still in testing)
```bash
sudo apt install git
git clone https://github.com/Brownster/ipod-dock.git
cd ipod-dock
```

A helper script `install.sh` automates dependency installation and sets up the
systemd service units. Run it from the project root:

```bash
./install.sh
```

Or of you prefer this will get the job done

```bash
sudo apt install git -y && sudo git clone https://github.com/Brownster/ipod-dock.git && cd ipod-dock && sudo ./install.sh
```


The installer copies the project to `/opt/ipod-dock` so the services run from a
path accessible to the `ipod` user. It creates or updates that user with
`/opt/ipod-dock` as its home, installs the unit files under `/etc/systemd/system`
and sets up a Python virtual environment with the dependencies. Ownership of the
target directory is updated accordingly. Start the services with:


```bash
sudo systemctl start ipod-api.service ipod-watcher.service ipod-listener.service
```

The services run under the dedicated `ipod` account. `install.sh` now installs
a `udev` rule and `ipod-mount.service` so the iPod's data partition is
mounted automatically when connected. The service detects the first FAT
partition and mounts it at `/opt/ipod-dock/mnt/ipod` using appropriate
`uid`, `gid` and `umask` options so the `ipod` user has access. If you prefer
manual control the script also adds an `/etc/fstab` entry so the `ipod` user
can mount the device without privileges. Adjust the device path in `/etc/fstab`
if needed; the default entry looks like:

```

/dev/disk/by-label/IPOD /opt/ipod-dock/mnt/ipod vfat noauto,user,uid=ipod,gid=ipod 0 0
```

If you prefer, remove the ``User=`` line from ``*.service`` files so they run
as ``root`` instead of granting mount permissions. Either approach works; the
example above keeps the service unprivileged by allowing the ``ipod`` user to
mount.

### Running unprivileged

If you keep ``ipod-listener`` as a non-root service, ``install.sh`` adds the
required sudoers rule automatically. The entry looks like this (replace
``ipodsvc`` with your service user if adding manually):

```
ipodsvc ALL=(root) NOPASSWD: \
    /bin/mount -t vfat /dev/disk/by-label/IPOD /opt/ipod-dock/mnt/ipod, \
    /bin/umount /opt/ipod-dock/mnt/ipod
```

The listener auto-detects when it is not running as uid 0 and silently prefixes
those commands with ``sudo --non-interactive --``.

Label the iPod's FAT partition once with:

```bash
sudo fatlabel /dev/sdX2 IPOD
```

The listener service attempts to detect the correct FAT partition
automatically when the iPod is connected.  You can override the detected
device by passing ``--device`` to the scripts or updating
``config.IPOD_DEVICE``.

After updating `fstab` you can test with:

```bash
sudo -u ipod mount /opt/ipod-dock/mnt/ipod
```

Once `ipod-api.service` is running you can open the web dashboard in a browser.
On the Pi itself visit `http://localhost:8000/`; from another machine replace
`localhost` with the Pi's address.

If you prefer to perform the steps manually, install the required system
packages (on Raspberry Pi OS):

```bash
sudo apt-get update
sudo apt-get install libgpod-common ffmpeg
```

`install.sh` and `update.sh` install `audible-cli` automatically. Run the
quickstart afterwards to authenticate:

```bash
audible quickstart
```

Sadly debain distro bookworm does not provide the `python3-gpod` package, running
`install.sh` will build the libgpod bindings from a maintained fork
([`john8675309/libgpod-0.8.3`](https://github.com/john8675309/libgpod-0.8.3))
with Python 3 support. This requires the SQLite development headers and libxml2
development files which can be installed with:

```bash
sudo apt-get install libsqlite3-dev libxml2-dev
```

The script also installs other build tools such as `automake`.

Create a Python virtual environment in the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This repository will use the virtual environment for any Python tools and future dependencies.

## Updating

Run `./update.sh` from the same project directory used during installation to refresh the copy under `/opt/ipod-dock`.
The script synchronises files, updates Python dependencies and restarts the services while preserving logs and uploaded data.


## Syncing files

During the early development phase queued files can be synced manually using the
`sync_from_queue` module:

```bash
python -m ipod_sync.sync_from_queue --device /dev/disk/by-label/IPOD
```

Any audio files placed in the `sync_queue/` directory will be imported to the
iPod and removed from the queue. Files using formats the iPod cannot play are
converted to MP3 using `ffmpeg` as part of this process.

Log output is written to `logs/ipod_sync.log` and rotated automatically. See
`docs/development.md` for developer notes on the logging configuration.


## Web API

A small FastAPI application exposes upload and track management endpoints. Start
the server for development with:

```bash
python -m ipod_sync.app
```

With the server running, navigate to `http://localhost:8000/` (or use the Pi's
address) to use the HTML dashboard for uploads and track browsing.

The `/status` endpoint now reports whether the configured iPod device is
connected via a `connected` boolean field. This value is derived from the
`ipod_connected` file written when the device is mounted.

See [docs/development.md](docs/development.md) for the list of endpoints.
Plugin developers can find usage examples in
[docs/plugin_api.md](docs/plugin_api.md).

## Continuous Integration

Unit tests run automatically on GitHub Actions for every push and pull request. The workflow installs the required Python packages from `requirements.txt` and executes `pytest`.

For a more detailed overview of the repository layout and development workflow
see [docs/developer_guide.md](docs/developer_guide.md).
