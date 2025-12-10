from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django import dispatch
from django.db.models.signals import post_save
from lib.celery import delay_task

from querycsv.models import QueryCsvUploadJob
from querycsv.tasks import process_csv_job_task

####################
# Signal Producers #
####################

process_csv_job_signal = dispatch.Signal()


def send_process_csv_job_signal(job: QueryCsvUploadJob):
    """Sends signal for queueing up a csv upload job."""

    process_csv_job_signal.send(job.__class__, instance=job)


####################
# Signal Receivers #
####################


@dispatch.receiver(process_csv_job_signal)
def on_process_csv_job_signal(sender, instance: Optional[QueryCsvUploadJob], **kwargs):
    """
    Runs when the process upload job signal is fired.

    This will create a new celery task for processing a csv upload.
    """

    if not instance:
        return

    delay_task(process_csv_job_task, job_id=instance.pk)


@dispatch.receiver(post_save, sender=QueryCsvUploadJob)
def on_job_log_save_signal(
    sender, instance: QueryCsvUploadJob, created=False, **kwargs
):
    """
    Runs when a log is saved to a Job

    This signals the channel to update for all listeners
    """

    channel_layer = get_channel_layer()

    event = {"type": "job_update"}

    async_to_sync(channel_layer.group_send)(f"job_{instance.pk}", event)
