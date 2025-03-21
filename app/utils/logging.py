"""
Logging and exception utils.
"""

import logging
import traceback

from app.settings import TESTING


def print_error():  # pragma: no cover
    """Log an error with stacktrace that's been handled via try/except."""
    if TESTING:
        return

    tb = traceback.format_exc()
    logging.warning(tb)
