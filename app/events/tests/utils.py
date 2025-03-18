from datetime import datetime, timedelta
from typing import Optional

from django.utils import timezone

from clubs.models import Club
from events.models import Event, EventHost
from lib.faker import fake


def create_test_event(
    name: str = "Test event",
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
    host: Optional[Club] = None,
    secondary_hosts: Optional[list[Club]] = None,
    **kwargs,
):
    """Create valid event for unit tests."""
    event_start = (
        start_datetime if start_datetime else timezone.now() - timedelta(days=1)
    )
    event_end = end_datetime if end_datetime else timezone.now() + timedelta(days=1)
    location = kwargs.pop("location", "CSE A101")
    description = kwargs.pop("description", fake.sentence())

    event = Event.objects.create(
        name=name,
        start_at=event_start,
        end_at=event_end,
        location=location,
        description=description,
        **kwargs,
    )

    if host:
        EventHost.objects.create(event=event, club=host, primary=True)

    secondary_hosts = secondary_hosts or []

    for host in secondary_hosts:
        EventHost.objects.create(event=event, club=host)

    return event
