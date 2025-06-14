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


def test_dry_run_logs_without_sync(caplog):
    handler = watcher.QueueEventHandler("/dev/ipod", dry_run=True)
    event = _event(Path("/queue/file.mp3"))
    with mock.patch.object(watcher, "sync_queue") as mock_sync:
        with caplog.at_level(logging.INFO):
            handler.on_created(event)
        mock_sync.assert_not_called()
        assert "Dry-run" in caplog.text


def test_watch_starts_observer(monkeypatch, tmp_path):
    records = {}

    class FakeObserver:
        def __init__(self):
            records['created'] = True
        def schedule(self, handler, path, recursive=False):
            records['schedule'] = (path, recursive)
        def start(self):
            records['started'] = True
        def stop(self):
            records['stopped'] = True
        def join(self):
            records['joined'] = True

    monkeypatch.setattr(watcher, 'Observer', FakeObserver)
    monkeypatch.setattr(watcher.time, 'sleep', mock.Mock(side_effect=KeyboardInterrupt))

    watcher.watch(tmp_path, '/dev/ipod')

    assert records['started']
    assert records['schedule'][0] == str(tmp_path)
    assert records['schedule'][1] is False
    assert records['stopped']
    assert records['joined']


def test_main_parses_args(monkeypatch):
    called = {}

    def fake_watch(queue, device, dry_run=False):
        called['args'] = (queue, device, dry_run)

    monkeypatch.setattr(watcher, 'watch', fake_watch)
    monkeypatch.setattr(watcher, 'setup_logging', lambda: None)

    watcher.main(['--queue-dir', '/tmp/q', '--device', '/dev/x', '--dry-run'])

    assert called['args'] == (Path('/tmp/q'), '/dev/x', True)
