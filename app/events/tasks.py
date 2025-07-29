from celery import shared_task

from events.models import RecurringEvent
from events.services import RecurringEventService


@shared_task
def sync_recurring_event_task(recurring_event_id: int):
    """Sync all events for a recurring event."""

    instance = RecurringEvent.objects.get(id=recurring_event_id)
    RecurringEventService(instance).sync_events()
