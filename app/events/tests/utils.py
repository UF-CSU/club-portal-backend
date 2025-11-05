from datetime import datetime, timedelta
from typing import Optional

from clubs.models import Club
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from lib.faker import fake

from events.models import Event

EVENT_LIST_URL = reverse("api-events:event-list")
RECURRINGEVENT_LIST_URL = reverse("api-events:recurringevent-list")


def event_list_url(start_at: datetime = None, end_at: datetime = None):
    url = reverse("api-events:event-list")
    query_params = {}

    if start_at:
        query_params["start_at"] = start_at
    if end_at:
        query_params["end_at"] = end_at

    if query_params:
        return f"{url}?{urlencode(query_params)}"

    return url


def event_attendance_list_url(event_id: int):
    return reverse("api-events:attendance-list", args=[event_id])


def event_detail_url(event_id: int):
    return reverse("api-events:event-detail", args=[event_id])


def create_test_event(
    host: Optional[Club] = None,
    secondary_hosts: Optional[list[Club]] = None,
    **kwargs,
):
    """Create valid event for unit tests."""
    payload = {
        "name": fake.title(),
        "location": fake.address(),
        "description": fake.paragraph(),
        "start_at": timezone.now() + timedelta(hours=1),
        "end_at": timezone.now() + timedelta(hours=3),
        "host": host,
        "secondary_hosts": secondary_hosts,
        "enable_attendance": False,
        **kwargs,
    }

    return Event.objects.create(**payload)


def create_test_events(count=5, **kwargs):
    """Create multiple mock events."""

    event_ids = [create_test_event(**kwargs).id for _ in range(count)]
    return Event.objects.filter(id__in=event_ids).all()
