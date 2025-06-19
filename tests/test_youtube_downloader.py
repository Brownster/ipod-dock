from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync import youtube_downloader


def test_download_audio_creates_path(tmp_path):
    mock_dl = mock.MagicMock()
    mock_dl.__enter__.return_value = mock_dl
    mock_dl.extract_info.return_value = {"id": "1", "ext": "webm"}
    mock_dl.prepare_filename.return_value = str(tmp_path / "music" / "foo.webm")
    with mock.patch("ipod_sync.youtube_downloader.YoutubeDL", return_value=mock_dl):
        path = youtube_downloader.download_audio("http://yt", "music", tmp_path)
    assert path == tmp_path / "music" / "foo.mp3"
    mock_dl.extract_info.assert_called_once_with("http://yt", download=True)
