from datetime import date, datetime, timedelta

import dateutil
from django.utils import timezone


def get_day_count(start: date, end: date, weekday: int):
    """
    Calculate the remaining amount of a weekday in a time range.

    Example
    -------
    Amount of Wednesdays (2) between 10-4-24 and 10-31-24

    Result: 4 Wednesdays in that range, between 5 calendar weeks,
    with the 1st Wednesday truncated because it falls before the range.
    """
    start_day = start.weekday()
    end_day = end.weekday()

    # Normalize dates, set to target weekday in that week
    start_date = start - timedelta(days=start.weekday()) + timedelta(days=weekday)
    end_date = end - timedelta(days=end.weekday()) + timedelta(days=weekday)

    # Weeks between normalized dates
    weeks = ((end_date - start_date).days / 7) + 1  # account for first week

    # If start is before weekday, remove day
    if start_day > weekday:
        weeks -= 1

    # If end is after weekday, remove day
    if end_day < weekday:
        weeks -= 1

    return int(weeks)


def parse_datetime(target: str | datetime, tzinfo=None):
    """Parse a string to a python datetime."""

    tzinfo = tzinfo or timezone.get_current_timezone()

    if isinstance(target, datetime) and target.tzinfo is None:
        return target.replace(tzinfo=tzinfo)
    elif isinstance(target, datetime):
        return target.astimezone(tzinfo)

    return dateutil.parser.parse(target).replace(tzinfo=tzinfo)


def parse_date(target: str | datetime | date, tzinfo=None, fail_silently=True):
    """
    Parse a string to a python date.
    Will return None if fail_silently is True and date is invalid.
    """

    try:
        if isinstance(target, date):
            target = datetime(year=target.year, month=target.month, day=target.day)

        return parse_datetime(target, tzinfo=tzinfo).date()
    except dateutil.parser._parser.ParserError as e:
        if not fail_silently:
            raise e

        return None
