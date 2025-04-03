import logging
from typing import Type

from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from core.abstracts.serializers import ModelSerializerBase
from querycsv.forms import CsvHeaderMappingFormSet, CsvUploadForm
from querycsv.models import QueryCsvUploadJob
from querycsv.services import QueryCsvService
from querycsv.signals import send_process_csv_job_signal


class QueryCsvViewSet:
    serializer_class: Type[ModelSerializerBase]

    def __init__(
        self,
        serializer_class: Type[ModelSerializerBase],
        get_reverse: callable,
        message_user_fn=None,
    ):
        self.serializer_class = serializer_class
        self.serializer = serializer_class()
        self.service = QueryCsvService(serializer_class)
        self.get_reverse = get_reverse
        self.message_user = message_user_fn

        def message_user_fallback(*args, **kwargs):
            pass

        if not self.message_user:
            self.message_user = message_user_fallback

    def upload_csv(self, request: HttpRequest, extra_context=None):
        """Upload csv for processing."""
        context = extra_context if extra_context else {}

        context["template_url"] = self.get_reverse("csv_template")
        context["all_fields"] = self.service.flat_fields.values()
        context["unique_together_fields"] = (
            self.serializer_class().unique_together_fields
        )

        # Not able to upload csv if no serializer is set
        if self.serializer_class is None:
            return TemplateResponse(
                request, "admin/querycsv/upload_not_available.html", context
            )

        if request.POST:
            form = CsvUploadForm(data=request.POST, files=request.FILES)

            if form.is_valid():
                # Process new csv
                job = QueryCsvUploadJob.objects.create(
                    serializer_class=self.serializer_class,
                    notify_email=request.user.email,
                    file=request.FILES["file"],
                )

                return redirect(self.get_reverse("upload_headermapping"), id=job.id)
            else:
                context["form"] = form

                return TemplateResponse(
                    request, "admin/querycsv/upload_csv.html", context=context
                )
        else:
            context["form"] = CsvUploadForm()

        return TemplateResponse(
            request, "admin/querycsv/upload_csv.html", context=context
        )

    def map_upload_csv_headers(self, request: HttpRequest, id: int, extra_context=None):
        """Given a csv upload job, define custom mappings between csv headers and object fields."""

        job = get_object_or_404(QueryCsvUploadJob, id=id)
        # TODO: What to do if job is completed, or url is visited for a previous job

        context = {
            **(extra_context or {}),
            "upload_job": job,
            "model_class_name": job.model_class.__name__,
        }

        if request.POST:
            formset = CsvHeaderMappingFormSet(request.POST, upload_job=job)

            if formset.is_valid():
                custom_mappings = [
                    mapping
                    for mapping in formset.cleaned_data
                    if mapping["csv_header"] != mapping["object_field"]
                ]

                for mapping in custom_mappings:
                    job.add_field_mapping(
                        column_name=mapping["csv_header"],
                        field_name=mapping["object_field"],
                        commit=False,
                    )

                job.save()

                send_process_csv_job_signal(job)
                self.message_user(request, "Successfully uploaded csv.", logging.INFO)

                return redirect(self.get_reverse())

        else:
            initial_data = []

            for header in job.csv_headers:
                cleaned_header = header.strip().lower().replace(" ", "_")
                # if cleaned_header in self.serializer.all_field_names:
                if cleaned_header in self.service.flat_fields.keys():
                    initial_mapping = {
                        "csv_header": header,
                        "object_field": cleaned_header,
                    }
                else:
                    initial_mapping = {"csv_header": header, "object_field": "pass"}

                initial_data.append(initial_mapping)

            formset = CsvHeaderMappingFormSet(initial=initial_data, upload_job=job)

        context["formset"] = formset

        return TemplateResponse(
            request, "admin/querycsv/upload_csv_headermapping.html", context=context
        )
