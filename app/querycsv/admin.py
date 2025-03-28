from django.contrib import admin

from core.abstracts.admin import ModelAdminBase
from querycsv.models import QueryCsvUploadJob
from querycsv.signals import send_process_csv_job_signal
from utils.formatting import plural_noun


class QueryCsvUploadJobAdmin(ModelAdminBase):
    """Manage upload jobs in admin."""

    list_display = ("__str__", "status", "created_at")
    actions = ("rerun_jobs",)

    @admin.action(description="Rerun Selected Jobs")
    def rerun_jobs(self, request, queryset):
        """Reruns a csv upload job."""

        for job in queryset.all():
            send_process_csv_job_signal(job)

        self.message_user(
            request,
            f"Successfully scheduled {queryset.count()} {plural_noun(queryset.count(), 'job')} to run.",
        )

        return


admin.site.register(QueryCsvUploadJob, QueryCsvUploadJobAdmin)
