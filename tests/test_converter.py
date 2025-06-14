from pathlib import Path
from unittest import mock
import subprocess

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

import ipod_sync.converter as converter


def test_needs_conversion():
    assert not converter.needs_conversion(Path("song.mp3"))
    assert converter.needs_conversion(Path("track.flac"))


@mock.patch("ipod_sync.converter.subprocess.run")
def test_convert_audio_invokes_ffmpeg(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
    src = tmp_path / "a.flac"
    src.write_text("x")
    dest = tmp_path / "a.mp3"
    converter.convert_audio(src, dest)
    assert mock_run.call_args[0][0][0] == "ffmpeg"
    assert str(src) in mock_run.call_args[0][0]
    assert str(dest) in mock_run.call_args[0][0]


@mock.patch("ipod_sync.converter.convert_audio")
def test_prepare_for_sync_conversion(mock_conv, tmp_path):
    src = tmp_path / "file.ogg"
    src.write_text("x")
    result = converter.prepare_for_sync(src)
    conv_path = src.with_suffix(".mp3")
    mock_conv.assert_called_once_with(src, conv_path)
    assert result == conv_path


@mock.patch("ipod_sync.converter.convert_audio")
def test_prepare_for_sync_no_conversion(mock_conv, tmp_path):
    src = tmp_path / "track.mp3"
    src.write_text("x")
    result = converter.prepare_for_sync(src)
    mock_conv.assert_not_called()
    assert result == src
