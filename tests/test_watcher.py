import logging
from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ipod_sync.watcher as watcher


def _event(path: Path):
    return mock.Mock(src_path=str(path), dest_path=str(path), is_directory=False)


def test_created_event_triggers_sync():
    handler = watcher.QueueEventHandler("/dev/ipod")
    event = _event(Path("/queue/foo.mp3"))
    with mock.patch.object(watcher, "sync_queue") as mock_sync:
        handler.on_created(event)
        mock_sync.assert_called_once_with("/dev/ipod")


def test_sync_exception_logged(caplog):
    handler = watcher.QueueEventHandler("/dev/ipod")
    event = _event(Path("/queue/foo.mp3"))
    with mock.patch.object(watcher, "sync_queue", side_effect=RuntimeError("boom")):
        with caplog.at_level(logging.ERROR):
            handler.on_created(event)
        assert "boom" in caplog.text


def test_should_ignore_temp_and_hidden_files():
    assert watcher._should_ignore("/path/.hidden")
    assert watcher._should_ignore("/path/foo.tmp")
    assert watcher._should_ignore("/path/foo.swp")
    assert watcher._should_ignore("/path/foo~")
    assert watcher._should_ignore("/path/foo.part")
    assert not watcher._should_ignore("/path/foo.mp3")


def test_ignored_event_does_not_sync():
    handler = watcher.QueueEventHandler("/dev/ipod")
    event = _event(Path("/queue/.foo.swp"))
    with mock.patch.object(watcher, "sync_queue") as mock_sync:
        handler.on_created(event)
        mock_sync.assert_not_called()
