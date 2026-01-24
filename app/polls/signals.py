from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from clubs.models import Club
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from events.models import Event

from polls.cache import delete_repopulate_poll_preview_cache
from polls.models import (
    Poll,
    PollField,
    PollInputType,
    PollSubmission,
    PollSubmissionLink,
)
from polls.serializers import PollSubmissionSerializer
from polls.services import PollService


@receiver(post_save, sender=Poll)
def on_save_poll(sender, instance: Poll, created=False, **kwargs):
    """Automations to run when poll is saved."""

    service = PollService(instance)

    if not instance.user_lookup_question:
        service.create_question(
            "Email",
            input_type=PollInputType.EMAIL,
            is_required=True,
            is_user_lookup=True,
        )

    if instance.are_tasks_out_of_sync:
        service.sync_status_tasks()

    if instance.submission_link is None and instance.club is not None:
        service.create_submission_link()


@receiver(post_save, sender=PollSubmission)
def on_save_poll_submission(sender, instance: PollSubmission, created=False, **kwargs):
    """Automations to run when poll submission is saved."""

    channel_layer = get_channel_layer()
    data = PollSubmissionSerializer(instance).data

    event = {"data": data}

    if created:  # Poll submission creation
        event["type"] = "submission_create"
    else:  # Poll submission update
        event["type"] = "submission_update"

    async_to_sync(channel_layer.group_send)(
        f"poll_{instance.poll.id}",
        event,
    )


@receiver(post_delete, sender=PollSubmission)
def on_delete_poll_submission(sender, instance: PollSubmission, **kwargs):
    """Automations to run when poll submission is deleted."""

    channel_layer = get_channel_layer()
    data = instance.id

    event = {
        "type": "submission_delete",
        "data": data,
    }

    async_to_sync(channel_layer.group_send)(
        f"poll_{instance.poll.id}",
        event,
    )


@receiver([post_save, post_delete])
def refresh_poll_preview_cache(
    sender,
    instance: Poll | Event | Club | PollField | PollSubmissionLink,
    created=False,
    **kwargs,
):
    """Sets and invalidates poll previews cache when relations change"""
    if sender in [Poll, Event, Club, PollField, PollSubmissionLink]:
        delete_repopulate_poll_preview_cache(instance)
