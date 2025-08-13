from django.db.models.signals import post_save
from django.dispatch import receiver

from polls.models import Poll
from polls.services import PollService


@receiver(post_save, sender=Poll)
def on_save_poll(sender, instance: Poll, created=False, **kwargs):
    """Automations to run when poll is saved."""

    if instance.are_tasks_out_of_sync:
        PollService(instance).sync_status_tasks()
