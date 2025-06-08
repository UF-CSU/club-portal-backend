from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils.safestring import mark_safe

from querycsv.models import CsvUploadStatus, QueryCsvUploadJob
from querycsv.services import QueryCsvService
from utils.helpers import import_from_path


@shared_task
def upload_csv_task(filepath: str, serializer_path: str):
    Serializer = import_from_path(serializer_path)
    svc = QueryCsvService(serializer_class=Serializer)

    qs = svc.upload_csv(filepath)
    print("Created objects:", qs)


@shared_task
def process_csv_job_task(job_id: int):
    """
    Processes a predefined upload job.
    Used for larger uploads.
    """
    # Process job
    job = QueryCsvUploadJob.objects.find_by_id(job_id)
    success, failed = QueryCsvService.upload_from_job(job)
    job.refresh_from_db()

    # Send admin email
    model_name = job.model_class._meta.verbose_name_plural
    if job.status != CsvUploadStatus.FAILED and job.notify_email:
        # Job was a success
        mail = EmailMultiAlternatives(
            subject=f"Upload {model_name} report",
            to=[job.notify_email],
            body=mark_safe(
                f"Your {model_name} csv has finished processing. "
                f"Objects processed successfully: {len(success)}. "
                f"Objects unsuccessfully processed: {len(failed)}."
            ),
        )
        mail.attach_alternative(
            (
                f"Your {model_name} csv has finished processing.<br><br>"
                f"Objects processed successfully: {len(success)}<br>"
                f"Objects unsuccessfully processed: {len(failed)}"
            ),
            "text/html",
        )
        mail.attach_file(job.report.path)
        mail.send()
    elif job.notify_email:
        # Job raised a parsing error
        mail = EmailMultiAlternatives(
            subject=f"Upload {model_name} report",
            to=[job.notify_email],
            body=mark_safe(
                f"Your {model_name} csv did not upload successfully. Received the following error: "
                f"{job.error or 'Unknown Error'}"
            ),
        )
        mail.attach_alternative(
            (
                f"Your {model_name} csv did not upload successfully. Received the following error:<br><br>"
                f"{job.error or 'Unknown Error'}"
            ),
            "text/html",
        )
