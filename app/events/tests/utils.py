import random
from datetime import UTC, datetime, timedelta
from typing import Optional

from clubs.models import Club
from core.abstracts.models import Color
from django.urls import reverse
from django.utils import timezone
from lib.faker import fake
from utils.dates import parse_datetime
from utils.helpers import reverse_query

from events.models import Event, EventTag

EVENT_LIST_URL = reverse("api-events:event-list")
EVENTPREVIEW_LIST_URL = reverse("api-events:eventpreview-list")
RECURRINGEVENT_LIST_URL = reverse("api-events:recurringevent-list")


def event_list_url(
    start_at: Optional[datetime] = None, end_at: Optional[datetime] = None
):
    """Get URL for listing full events."""

    query_params = {}

    if start_at:
        query_params["start_at"] = start_at.astimezone(UTC).strftime(
            "%Y-%m-%d %H:%M:%SZ"
        )
    if end_at:
        query_params["end_at"] = end_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%SZ")

    return reverse_query("api-events:event-list", query_params)


def event_preview_list_url(
    start_at: Optional[datetime] = None, end_at: Optional[datetime] = None
):
    """Get URL for listing event previews."""

    query_params = {}

    if start_at:
        query_params["start_at"] = start_at
    if end_at:
        query_params["end_at"] = end_at

    return reverse_query("api-events:eventpreview-list", query_params)


def event_attendance_list_url(event_id: int):
    """Get URL for listing event attendance data."""

    return reverse("api-events:attendance-list", args=[event_id])


def event_detail_url(event_id: int):
    """Get URL for viewing a single event."""

    return reverse("api-events:event-detail", args=[event_id])


def event_preview_detail_url(event_id: int):
    """Get URL for viewing a single event preview."""

    return reverse("api-events:eventpreview-detail", args=[event_id])


def create_test_eventtag(**kwargs):
    """Create mock event tag for testing."""

    payload = {
        "name": fake.title(),
        "color": random.choice(Color.choices)[0],
        **kwargs,
    }

    return EventTag.objects.create(**payload)


def create_test_event(
    host: Optional[Club] = None,
    secondary_hosts: Optional[list[Club]] = None,
    start_at: Optional[str | datetime] = None,
    end_at: Optional[str | datetime] = None,
    **kwargs,
):
    """Create valid event for unit tests."""

    if start_at is not None:
        kwargs["start_at"] = parse_datetime(start_at)

    if end_at is not None:
        kwargs["end_at"] = parse_datetime(end_at)

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
