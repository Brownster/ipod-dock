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
