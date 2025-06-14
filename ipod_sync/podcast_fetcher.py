from __future__ import annotations

"""Utilities for downloading podcast episodes from RSS feeds."""

import logging
from pathlib import Path
import urllib.request

import feedparser

from . import config

logger = logging.getLogger(__name__)


def fetch_podcasts(feed_url: str, queue_dir: Path | None = None) -> list[Path]:
    """Download podcast episodes from *feed_url* into the sync queue.

    Parameters
    ----------
    feed_url:
        URL of the RSS feed to parse.
    queue_dir:
        Base directory for queued files. Defaults to
        ``config.SYNC_QUEUE_DIR / 'podcast'``.

    Returns
    -------
    list[Path]
        Paths of downloaded files.
    """

    queue = Path(queue_dir) if queue_dir else Path(config.SYNC_QUEUE_DIR) / "podcast"
    queue.mkdir(parents=True, exist_ok=True)

    feed = feedparser.parse(feed_url)
    downloaded: list[Path] = []

    for entry in getattr(feed, "entries", []):
        for enc in getattr(entry, "enclosures", []):
            href = enc.get("href")
            if not href:
                continue
            filename = Path(href).name.split("?")[0]
            dest = queue / filename
            if dest.exists():
                continue
            try:
                logger.info("Downloading %s", href)
                urllib.request.urlretrieve(href, dest)
                downloaded.append(dest)
            except Exception as exc:  # pragma: no cover - network failures
                logger.error("Failed to download %s: %s", href, exc)
    return downloaded


if __name__ == "__main__":  # pragma: no cover - manual execution
    import argparse

    parser = argparse.ArgumentParser(description="Fetch podcast episodes from an RSS feed")
    parser.add_argument("feed_url")
    args = parser.parse_args()

    setup_logging = getattr(__import__("ipod_sync.logging_setup", fromlist=["setup_logging"]), "setup_logging")
    setup_logging()
    fetched = fetch_podcasts(args.feed_url)
    for path in fetched:
        print(path)
