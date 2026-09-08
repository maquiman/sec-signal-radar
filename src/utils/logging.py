from __future__ import annotations

import logging
from pathlib import Path

from src.utils.config import CACHE_DIR


def get_logger(name: str) -> logging.Logger:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(Path(CACHE_DIR) / "screener.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
