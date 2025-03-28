"""
Global formatting utility functions.
"""

from typing import Optional


def plural_noun(count_target: list | int, singular: str, plural: Optional[str] = None):
    """Takes a list or number and will return singlar form if 1, plural form otherwise."""
    plural = plural if plural else f"{singular}s"
    count = count_target

    if isinstance(count_target, list):
        count = len(count_target)

    return plural if count != 1 else singular


BYTE_UNITS = (
    (1 << 50, " PB"),
    (1 << 40, " TB"),
    (1 << 30, " GB"),
    (1 << 20, " MB"),
    (1 << 10, " KB"),
    (1, (" byte", " bytes")),
)


def format_bytes(bytes_count: int):
    """Take a raw number of bytes and return a string representing the amount in megabytes."""
    unit_size = 0
    unit_label = ""

    for size, unit in BYTE_UNITS:
        if bytes_count >= size:
            unit_size = round(bytes_count / size, 2)
            if unit_size > 100:
                unit_size = int(unit_size)
            unit_label = unit
            break

    if isinstance(unit_label, tuple):
        singular, plural = unit_label
        if unit_size == 1:
            unit_label = singular
        else:
            unit_label = plural

    return str(unit_size) + unit_label
