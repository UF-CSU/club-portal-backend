from typing import Optional

from django import dispatch

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
