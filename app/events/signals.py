from django.db.models.signals import post_save
from django.dispatch import receiver

from events.models import Event
from events.services import EventService


@receiver(post_save, sender=Event)
def on_save_event(sender, instance: Event, created=False, **kwargs):
    """Automations to run when event is saved."""

    service = EventService(instance)

    # Create an attendance link for each club.
    # Each link will create the same attendance object, but
    # this allows each club to track their own marketing effectiveness.
    service.sync_hosts_attendance_links()

    # Make a job for scheduling event as public
    if instance.make_public_task is None and instance.make_public_at is not None:
        service.schedule_make_public_task()
