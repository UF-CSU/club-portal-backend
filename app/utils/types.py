"""
Type utilities.
"""

from typing import Any, TypeVar

T = TypeVar("T")


def islistinstance(target: list | Any, class_type, check_all=False):
    """Check if list items are a certain type."""

    if not isinstance(target, list):
        return False

    if len(target) == 0:
        return False

    if not check_all:
        return isinstance(target[0], class_type)

    for item in target:
        if not isinstance(item, class_type):
            return False

    return True
