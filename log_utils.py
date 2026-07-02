"""Логирование запросов ChatList."""

from __future__ import annotations

import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "chatlist.log"

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("chatlist")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)

    _logger = logger
    return logger
