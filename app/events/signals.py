from django.db.models.signals import post_save
from django.dispatch import receiver

from events.models import Event, RecurringEvent
from events.services import EventService


@receiver(post_save, sender=RecurringEvent)
def on_save_recurring_event(sender, instance: RecurringEvent, created=False, **kwargs):
    """Automations to run when a recurring event is saved."""

    # Only proceed if event is being created
    if not created:
        return

    EventService.sync_recurring_event(instance)


@receiver(post_save, sender=Event)
def on_save_event(sender, instance: Event, created=False, **kwargs):
    """Automations to run when event is saved."""

    # Create an attendance link for each club.
    # Each link will create the same attendance object, but
    # this allows each club to track their own marketing effectiveness.
    EventService(instance).sync_hosts_attendance_links()
