# Developer Notes

This document outlines helper utilities and how to run the unit tests while
working on the project.

## Mount helpers

`ipod_sync.utils` provides small wrappers for mounting and ejecting the iPod.
They call the system `mount`, `umount` and `eject` commands using Python's
`subprocess` module and log any output for debugging. The helpers are:

- `mount_ipod(device: str)` – mounts the given block device to the configured
  `IPOD_MOUNT` directory.
- `eject_ipod()` – unmounts and ejects whatever is mounted at `IPOD_MOUNT`.

Both functions raise a `RuntimeError` if the underlying command fails.

## Running tests

The repository uses `pytest` for unit tests. Simply run:

```bash
pytest
```

The tests mock out system calls so they run quickly and without requiring an
iPod to be attached.

## libgpod wrapper

`ipod_sync.libpod_wrapper` contains helper functions that wrap the optional
`python-gpod` bindings.  These bindings are not installed by default in the test
environment, so the unit tests mock them out.  On a Debian based system you can
install them via:

```bash
sudo apt-get install libgpod-common
```

If `python3-gpod` isn't packaged on your system, the `install.sh` script will
download and build the bindings automatically and install required build tools
such as `automake`.

The module exposes three simple helpers:

- `add_track(path)` – import a file into the mounted iPod database.
- `delete_track(db_id)` – remove a track by its database identifier.
- `list_tracks()` – return a list of basic metadata for each track.

If the bindings are missing a `RuntimeError` will be raised when any of these
functions are called.

## Syncing from the queue

`ipod_sync.sync_from_queue` provides a helper script to import any files placed
in the `sync_queue/` directory.  It mounts the configured iPod device, calls
`add_track()` for each queued file and ejects the iPod once finished.  By
default files are removed from the queue after a successful import.

Run the script manually with:

```bash
python -m ipod_sync.sync_from_queue --device /dev/sda1
```

The `--device` argument may be omitted if your iPod is available at the default
path configured in `config.IPOD_DEVICE`.

## Logging

The project writes application logs to `logs/ipod_sync.log`.  Logging is
configured by `ipod_sync.logging_setup.setup_logging()` which installs a
`RotatingFileHandler` keeping up to three 1 MB log files.  Unit tests use this
helper to create temporary log files.

## Web API

The `ipod_sync.app` module exposes a small FastAPI application. Run a local
server with:

```bash
python -m ipod_sync.app
```

Endpoints:

- `GET /status` – simple health check returning `{"status": "ok"}`.
- `POST /upload` – upload a file; it is saved to `sync_queue/` for later sync.
- `POST /upload/{category}` – upload a file to a specific category (`music` or `audiobook`).
- `GET /tracks` – list tracks on the iPod. The iPod is mounted automatically.
- `DELETE /tracks/{id}` – remove a track by its database ID. The iPod is mounted
  and ejected for the operation.
- `GET /queue` – list files currently waiting in the sync queue.
- `POST /queue/clear` – remove all files from the queue.
- `POST /sync` – import queued files onto the iPod immediately.
- `GET /stats` – return counts for the dashboard (tracks, queue size, disk usage).

The API uses the same rotating log configuration as the sync script.

## Web UI

Start the FastAPI server and open `http://localhost:8000/` in a browser to see
the web dashboard.  The interface loads its CSS and JavaScript from the
`/static` directory and communicates with the API via `fetch()` calls.  Drag and
drop files onto the upload area, trigger a manual sync and browse tracks, queued
files or audiobooks from the tabbed view.

