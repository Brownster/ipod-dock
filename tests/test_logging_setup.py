from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipod_sync.logging_setup import setup_logging


def test_setup_logging_creates_rotating_handler(tmp_path):
    log_file = tmp_path / "my.log"
    setup_logging(log_file, level=logging.DEBUG)
    logger = logging.getLogger()
    handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
    assert Path(handler.baseFilename) == log_file
    logger.debug("test")
    assert log_file.exists()
