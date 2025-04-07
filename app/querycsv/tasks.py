import pandas as pd
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.safestring import mark_safe

from querycsv.consts import QUERYCSV_MEDIA_SUBDIR
from querycsv.models import CsvUploadStatus, QueryCsvUploadJob
from querycsv.services import QueryCsvService
from utils.files import get_media_path
from utils.helpers import import_from_path
from utils.models import save_file_to_model


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
    job.status = CsvUploadStatus.SUCCESS

    # Create report
    report_file_path = get_media_path(
        QUERYCSV_MEDIA_SUBDIR + f"reports/{job.model_class.__name__}/",
        fileprefix=str(timezone.now().strftime("%d-%m-%Y_%H:%M:%S")),
        fileext="xlsx",
    )

    success_report = pd.json_normalize(success)
    failed_report = pd.json_normalize(failed)

    with pd.ExcelWriter(report_file_path) as writer:
        success_report.to_excel(writer, sheet_name="Successful", index=False)
        failed_report.to_excel(writer, sheet_name="Failed", index=False)

    save_file_to_model(job, report_file_path, field="report")
    job.refresh_from_db()

    # Send admin email
    if job.notify_email:
        model_name = job.model_class._meta.verbose_name_plural
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
        mail.attach_file(report_file_path)
        mail.send()
