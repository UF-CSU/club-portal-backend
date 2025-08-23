from django.db.models.signals import post_save
from django.dispatch import receiver

from polls.models import Poll, PollInputType
from polls.services import PollService


@receiver(post_save, sender=Poll)
def on_save_poll(sender, instance: Poll, created=False, **kwargs):
    """Automations to run when poll is saved."""

    service = PollService(instance)

    if not instance.questions.filter(is_user_lookup=True).exists():
        service.create_question(
            "Email",
            input_type=PollInputType.EMAIL,
            is_required=True,
            is_user_lookup=True,
        )

    if instance.are_tasks_out_of_sync:
        service.sync_status_tasks()

    if instance.submission_link is None:
        service.create_submission_link()
