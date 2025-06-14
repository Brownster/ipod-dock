from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync import podcast_fetcher


def test_fetch_podcasts_downloads(tmp_path):
    feed = mock.Mock(entries=[
        mock.Mock(enclosures=[{"href": "http://example.com/ep.mp3"}])
    ])
    with mock.patch.object(podcast_fetcher.feedparser, "parse", return_value=feed):
        with mock.patch("urllib.request.urlretrieve") as urlret:
            urlret.side_effect = lambda url, dest: Path(dest).write_bytes(b"x")
            downloaded = podcast_fetcher.fetch_podcasts("http://feed", tmp_path)
    assert (tmp_path / "ep.mp3").exists()
    assert downloaded == [tmp_path / "ep.mp3"]
