"""
Logging and exception utils.
"""

import logging
import traceback
from typing import Optional

from app.settings import TESTING


def print_error(
    print_in_tests=False, exc: Optional[Exception] = None
):  # pragma: no cover
    """Log an error with stacktrace that's been handled via try/except."""
    if TESTING and not print_in_tests:
        return

    if exc:
        try:
            raise exc
        except Exception:
            return print_error()

    tb = traceback.format_exc()
    logging.warning(tb)
