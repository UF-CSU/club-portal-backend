"""
CSV data logging models.
"""

import logging
from pathlib import Path
from typing import ClassVar, Optional, TypedDict

from django.core.files import File
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.abstracts.models import ManagerBase, ModelBase
from lib.spreadsheets import SPREADSHEET_EXTS, read_spreadsheet
from querycsv.consts import QUERYCSV_MEDIA_SUBDIR
from querycsv.serializers import CsvModelSerializer
from utils.files import get_file_path
from utils.formatting import format_timedelta
from utils.helpers import get_import_path, import_from_path
from utils.logging import print_error
from utils.models import UploadFilepathFactory, ValidateImportString


class CsvUploadStatus(models.TextChoices):
    """When a csv is uploaded, will have one of these statuses"""

    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    FAILED = "failed", _("Failed")
    SUCCESS = "success", _("Success")
    CONTAINS_ERRORS = "contains_errors", _("Contains Errors")
    INVALID = "invalid", _("Invalid CSV")


class FieldMappingType(TypedDict):
    column_name: str
    field_name: str


class QueryCsvUploadJobManager(ManagerBase["QueryCsvUploadJob"]):
    """Model manager for queryset csvs."""

    def create(
        self,
        serializer_class: type[serializers.Serializer],
        filepath: Optional[str] = None,
        notify_email: Optional[str] = None,
        **kwargs,
    ) -> "QueryCsvUploadJob":
        """
        Create new QuerySet Csv Upload Job.
        """

        kwargs["serializer"] = get_import_path(serializer_class)

        if filepath:
            path = Path(filepath)
            with path.open(mode="rb") as f:
                kwargs["file"] = File(f, name=path.name)
                job = super().create(notify_email=notify_email, **kwargs)
        else:
            job = super().create(notify_email=notify_email, **kwargs)

        return job


class QueryCsvUploadJob(ModelBase):
    """Used to store meta info about csvs from querysets."""

    validate_import_string = ValidateImportString(target_type=CsvModelSerializer)
    csv_upload_path = UploadFilepathFactory(
        path=QUERYCSV_MEDIA_SUBDIR + "uploads/", default_extension="csv"
    )

    # Primary fields
    file = models.FileField(
        upload_to=csv_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=SPREADSHEET_EXTS)],
    )
    serializer = models.CharField(
        max_length=64, validators=[validate_import_string], null=True
    )

    # Meta fields
    status = models.CharField(
        choices=CsvUploadStatus.choices, default=CsvUploadStatus.PENDING
    )
    notify_email = models.EmailField(null=True, blank=True)
    report = models.FileField(
        upload_to=QUERYCSV_MEDIA_SUBDIR + "reports/",
        null=True,
        blank=True,
        editable=False,
    )
    custom_field_mappings = models.JSONField(
        blank=True, help_text="Key value pairs, column name => model field"
    )
    error = models.CharField(null=True, blank=True, editable=False)
    success_count = models.PositiveIntegerField(null=True, blank=True, editable=False)
    failed_count = models.PositiveIntegerField(null=True, blank=True, editable=False)
    logs = models.JSONField(null=True, blank=True, editable=False)
    started_at = models.DateTimeField(null=True, blank=True, editable=False)
    ended_at = models.DateTimeField(null=True, blank=True, editable=False)

    # Overrides
    objects: ClassVar[QueryCsvUploadJobManager] = QueryCsvUploadJobManager()

    def save(self, *args, **kwargs) -> None:
        if self.custom_field_mappings is None:
            self.custom_field_mappings = {"fields": []}

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    class Meta:
        verbose_name = "CSV Upload"

    # Dynamic properties
    @cached_property
    def display_name(self):
        if self.filepath:
            return f'Upload for "{self.object_type}" objects, {self.row_count} rows'
        return f'Upload for "{self.object_type}" objects'

    @cached_property
    def filepath(self):
        return get_file_path(self.file)

    @cached_property
    def spreadsheet(self):
        if self.status == CsvUploadStatus.INVALID:
            return None

        try:
            return read_spreadsheet(self.filepath, self.file)
        except Exception as e:
            print_error()
            self.error = e
            self.status = CsvUploadStatus.INVALID
            self.save()
            return None

    @cached_property
    def row_count(self):
        if self.spreadsheet is not None:
            return len(self.spreadsheet.index)
        else:
            return 0

    @property
    def serializer_class(self) -> type[CsvModelSerializer]:
        return import_from_path(self.serializer)

    @serializer_class.setter
    def serializer_class(self, value: type[CsvModelSerializer]):
        self.serializer = get_import_path(value)

    @cached_property
    def model_class(self) -> type[ModelBase]:
        return self.serializer_class.Meta.model

    @cached_property
    def object_type(self):
        return self.model_class.__name__

    @property
    def custom_fields(self) -> list[FieldMappingType]:
        return self.custom_field_mappings["fields"]

    @property
    def ellapsed_time(self):
        if self.started_at and self.ended_at:
            return format_timedelta(
                self.ended_at - self.started_at, minutes=True, seconds=True
            )
        else:
            return "--"

    @cached_property
    def csv_headers(self):
        if self.spreadsheet is not None:
            return list(self.spreadsheet.columns)
        else:
            return []

    # Methods
    def start_clock(self):
        self.add_log("Starting upload...", commit=False)
        self.logs = {}
        self.started_at = timezone.now()
        self.ended_at = None
        self.save()

    def end_clock(self):
        self.add_log("Upload complete.", commit=False)
        self.ended_at = timezone.now()
        self.save()

    def add_log(self, msg: str, key: Optional[str] = None, commit=True):
        """Add log to json field."""

        if self.logs is None or "messages" not in self.logs.keys():
            self.logs = {"messages": []}

        if key is not None:
            self.logs[key] = msg
        else:
            msg = f"[{timezone.now()}] {msg}"
            self.logs["messages"].append(msg)
            logging.debug(msg)

        if not commit:
            return

        self.save()

    def add_field_mapping(self, column_name: str, field_name: str, commit=True):
        """Add custom field mapping."""

        if self.spreadsheet is not None:
            column_options = list(self.spreadsheet.columns)

            assert column_name in column_options, (
                f"The name {column_name} is not in available columns: {', '.join(column_options)}"
            )

        self.custom_field_mappings["fields"].append(
            {"column_name": column_name, "field_name": field_name}
        )

        if commit:
            self.save()
