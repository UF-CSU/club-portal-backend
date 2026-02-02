from core.abstracts.admin import ModelAdminBase
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from users.models import Ticket
from utils.admin import other_info_fields
from utils.formatting import plural_noun

from querycsv.models import QueryCsvUploadJob
from querycsv.signals import send_process_csv_job_signal


class QueryCsvUploadJobAdmin(ModelAdminBase):
    """Manage upload jobs in admin."""

    list_display = (
        "__str__",
        "id",
        "status",
        "success_count",
        "failed_count",
        "created_at",
        "updated_at",
    )
    actions = ("rerun_jobs",)
    readonly_fields = (
        "id",
        "success_count",
        "failed_count",
        "error",
        "row_count",
        "object_type",
        "created_at",
        "updated_at",
        "report",
        "upload_logs",
        "started_at",
        "ended_at",
        "ellapsed_time",
        "headers",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "file",
                    "serializer",
                    "row_count",
                    "object_type",
                ),
            },
        ),
        (
            _("Upload Status"),
            {
                "fields": (
                    "status",
                    "report",
                    "notify_email",
                    "success_count",
                    "failed_count",
                    "error",
                    "started_at",
                    "ended_at",
                    "ellapsed_time",
                )
            },
        ),
        (
            _("Field Mappings"),
            {
                "fields": (
                    "custom_field_mappings",
                    "headers",
                ),
            },
        ),
        (_("Logs"), {"fields": ("upload_logs",)}),
        other_info_fields,
    )

    def upload_logs(self, obj):
        json_logs = self.as_json(obj.logs)
        return mark_safe(f'<span id="job-log-list">{json_logs}</span>')
        # return obj.logs

    def headers(self, obj):
        return ", ".join(obj.csv_headers)

    def has_add_permission(self, request):
        return False

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

    def render_change_form(
        self, request, context, add=None, change=None, form_url=None, obj=None
    ):
        ticket, _ = Ticket.objects.get_or_create(user=request.user)
        context["ticket"] = ticket
        return super().render_change_form(request, context, add, change, form_url, obj)


admin.site.register(QueryCsvUploadJob, QueryCsvUploadJobAdmin)
