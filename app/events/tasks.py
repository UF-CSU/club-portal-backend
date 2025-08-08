from celery import shared_task

from events.models import Event, RecurringEvent
from events.services import EventService, RecurringEventService


@shared_task
def sync_event_attendance_links_task(event_ids=None):
    # event_ids = event_ids or list(Event.objects.all().values_list("id", flat=True))

    if event_ids:
        events = Event.objects.filter(id__in=event_ids).all()
    else:
        events = Event.objects.all()

    for event in events:
        EventService(event).sync_hosts_attendance_links()


@shared_task
def sync_recurring_event_task(recurring_event_id: int):
    """Sync all events for a recurring event."""

    instance = RecurringEvent.objects.get(id=recurring_event_id)
    RecurringEventService(instance).sync_events()
