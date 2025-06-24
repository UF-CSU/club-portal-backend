"""
Global formatting utility functions.
"""

from typing import Optional

from django.utils.timezone import timedelta


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


def format_timedelta(
    delta: timedelta, minutes=False, seconds=False, trim_on_weeks=True
):
    """
    Convert a datetime.timedelta object into Days, Hours, Minutes, Seconds
    Ref: https://stackoverflow.com/questions/16348003/displaying-a-timedelta-object-in-a-django-template
    """
    secs = delta.total_seconds()
    time_str = ""

    min_secs = 60
    hour_secs = min_secs * 60
    day_secs = hour_secs * 24
    week_secs = day_secs * 7

    has_weeks = True

    if secs > week_secs:
        weeks = int(secs // week_secs)
        time_str += f"{weeks} {plural_noun(weeks, 'week')}"
        secs = secs - weeks * week_secs
        has_weeks = True
    else:
        has_weeks = False

    if secs > day_secs:
        days = int(secs // day_secs)
        time_str += f" {days} {plural_noun(days, 'day')}"
        secs = secs - days * day_secs

    if secs > hour_secs and not (trim_on_weeks and has_weeks):
        hrs = int(secs // hour_secs)
        time_str += f" {hrs} {plural_noun(hrs, 'hour')}"
        secs = secs - hrs * hour_secs

    if secs > min_secs and minutes is True and not (trim_on_weeks and has_weeks):
        mins = int(secs // min_secs)
        time_str += f" {mins} {plural_noun(mins, 'minute')}"
        secs = secs - mins * min_secs

    if secs > 0 and seconds and not (trim_on_weeks and has_weeks):
        time_str += f" {int(secs)} seconds"

    # If was supposed to trim minutes, but it's been less than an hour,
    # then give how long ago the delta was in minutes.
    if time_str == "" and not minutes:
        time_str = format_timedelta(delta, minutes=True)

        if time_str == "":
            time_str = "Just now"
        else:
            time_str += " ago"

    return time_str.strip()
