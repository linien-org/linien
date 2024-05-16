import logging
from logging.handlers import RotatingFileHandler

import importlib_metadata

from .config import LOG_FILE_PATH

__version__ = importlib_metadata.version("linien-common")  # noqa: F401

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(str(LOG_FILE_PATH), maxBytes=1000000, backupCount=10)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter("%(name)-30s %(levelname)-8s %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)
