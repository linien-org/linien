import logging

import importlib_metadata

__version__ = importlib_metadata.version("linien-common")  # noqa: F401

logger = logging.getLogger(__name__)
