from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from lib.celery import delay_task
from polls.models import Poll

from events.models import Event, RecurringEvent
from events.services import EventService
from events.tasks import sync_recurring_event_task


@receiver(post_save, sender=Event)
def on_save_event(sender, instance: Event, created=False, **kwargs):
    """Automations to run when event is saved."""

    service = EventService(instance)

    if instance.enable_attendance and instance.primary_club:
        # Create an attendance link for each club.
        # Each link will create the same attendance object, but
        # this allows each club to track their own marketing effectiveness.
        service.sync_hosts_attendance_links()

        poll_open = instance.start_at - timezone.timedelta(minutes=30)
        poll_close = instance.end_at

        if not instance.poll:
            Poll.objects.create(
                name=instance.__str__(),
                event=instance,
                open_at=poll_open,
                close_at=poll_close,
                is_published=True,
                club=instance.primary_club,
            )
        else:
            instance.poll.open_at = poll_open
            instance.poll.close_at = poll_close
            instance.poll.save()

    # Make a job for scheduling event as public
    if instance.make_public_task is None and instance.make_public_at is not None:
        service.schedule_make_public_task()


# @receiver(post_save, sender=Event)
# def on_save_event_cache(sender, instance: Event, **kwargs):
#     """Sets the event cache when an event is saved"""
#     hosts = instance.hosts.all()
#     delete_repopulate_event_cache(hosts)


# @receiver(post_delete, sender=Event)
# def on_delete_event_cache(sender, instance: Event, **kwargs):
#     """Clear an event cache key on delete"""
#     hosts = instance.hosts.all()
#     delete_repopulate_event_cache(hosts)


@receiver(post_save, sender=RecurringEvent)
def on_save_recurring_event(sender, instance: RecurringEvent, created=False, **kwargs):
    """Makes recurring events creation process async"""

    if instance.is_synced:
        return

    if not instance.is_synced:
        # transaction.on_commit(lambda:delay_task(sync_recurring_event_task, recurring_event_id=instance.id))
        delay_task(sync_recurring_event_task, recurring_event_id=instance.id)
