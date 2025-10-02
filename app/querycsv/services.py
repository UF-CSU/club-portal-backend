import re
from collections import OrderedDict
from enum import Enum
from typing import Literal, Optional, TypedDict

import pandas as pd
from django.db import models
from django.utils import timezone

from core.abstracts.serializers import ModelSerializerBase
from lib.spreadsheets import read_spreadsheet
from querycsv.consts import QUERYCSV_MEDIA_SUBDIR
from querycsv.models import CsvUploadStatus, QueryCsvUploadJob
from querycsv.serializers import CsvModelSerializer
from utils.files import get_file_path, get_media_path
from utils.helpers import str_to_list
from utils.logging import print_error
from utils.models import save_file_to_model


class FieldMappingType(TypedDict):
    column_name: str
    field_name: str


class QueryCsvService:
    """Handle uploads and downloads of models using csvs."""

    class Actions(Enum):
        SKIP = "SKIP"
        CF = "CUSTOM_FIELD"

    def __init__(
        self,
        serializer_class: type[CsvModelSerializer],
        job: Optional[QueryCsvUploadJob] = None,
    ):
        self.serializer_class = serializer_class
        self.serializer = serializer_class()
        self.model_name = self.serializer.model_class.__name__

        self.fields: OrderedDict = self.serializer.get_fields()
        self.readonly_fields = self.serializer.readonly_fields
        self.writable_fields = self.serializer.writable_fields
        self.all_fields = self.serializer.readable_fields
        self.required_fields = self.serializer.required_fields
        self.unique_fields = self.serializer.unique_fields

        self.flat_fields = self.serializer.get_flat_fields()

        self.actions = [action.value for action in self.Actions]
        self.job = job

        # Calculate all available fields for forms
        all_fields = list(self.serializer.get_fields().keys())
        flat_fields = list(self.serializer.get_flat_fields().keys())
        self.available_fields = list(set(flat_fields + all_fields))
        self.available_fields.sort()

    @classmethod
    def upload_from_job(cls, job: QueryCsvUploadJob):
        """Upload csv using predefined job."""

        assert job.serializer is not None, "Upload job must container serializer."

        # Start processing job
        job.status = CsvUploadStatus.PROCESSING
        job.save()

        svc = cls(serializer_class=job.serializer_class, job=job)
        success, failed = svc.upload_csv(
            get_file_path(job.file), custom_field_maps=job.custom_fields
        )

        # Set final job status
        if not isinstance(failed, list):
            # Break circuit if failed
            job.status = CsvUploadStatus.FAILED
            job.error = failed
            job.save()

            return success, failed
        elif len(failed) > 0:
            job.status = CsvUploadStatus.CONTAINS_ERRORS
        else:
            job.status = CsvUploadStatus.SUCCESS

        job.success_count = len(success)
        job.failed_count = len(failed)

        job.save()

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

        return success, failed

    @classmethod
    def queryset_to_csv(
        cls, queryset: models.QuerySet, serializer_class: type[ModelSerializerBase]
    ):
        """Print a queryset to a csv, return file path."""

        service = cls(serializer_class=serializer_class)
        return service.download_csv(queryset)

    def _log_job_msg(self, msg: str):
        if self.job:
            self.job.add_log(msg)

    def _log_job_kwarg(self, key: str, value: str):
        if self.job:
            self.job.add_log(value, key=key)

    def download_csv(self, queryset: models.QuerySet) -> str:
        """Download: Convert queryset to csv, return path to csv."""

        data = self.serializer_class(queryset, many=True).data
        flattened = [self.serializer_class.json_to_flat(obj) for obj in data]

        df = pd.json_normalize(flattened)
        filepath = get_media_path(
            QUERYCSV_MEDIA_SUBDIR + "downloads/",
            fileprefix=f"{self.model_name}",
            fileext="csv",
        )
        df.to_csv(filepath, index=False)

        return filepath

    def get_csv_template(
        self, field_types: Literal["all", "required", "writable"]
    ) -> str:
        """
        Get path to csv file containing required fields for upload.

        Parameters
        ----------
            - all_fields (bool): Whether to include all fields or just required fields.

        Returns
        -------
            Path to csv template file.
        """

        flat_field_names = self.flat_fields.values()

        match field_types:
            case "required":
                template_fields = [
                    str(field) for field in flat_field_names if field.is_required
                ]
            case "writable":
                template_fields = [
                    str(field) for field in flat_field_names if field.is_writable
                ]
            case "all" | _:
                template_fields = [str(field) for field in flat_field_names]

        filepath = get_media_path(
            QUERYCSV_MEDIA_SUBDIR + "templates/",
            f"{self.model_name}_template.csv",
            create_path=True,
        )
        df = pd.DataFrame([], columns=template_fields)
        df.to_csv(filepath, index=False)

        return filepath

    def upload_csv(
        self, path: str, custom_field_maps: Optional[list[FieldMappingType]] = None
    ):
        """
        Upload: Given path to csv, create/update models and
        return successful and failed objects.
        """
        try:
            if self.job:
                self.job.start_clock()

            # Start by importing csv
            df = read_spreadsheet(path)
            self._log_job_msg(
                "Finished reading spreadsheet, processing field mappings..."
            )

            # Strip leading/trailing spaces from column names
            df.columns = df.columns.str.strip()

            # Update df values with header associations
            if custom_field_maps:
                generic_list_keys = []  # Used for determining index when ambiguous

                for mapping in custom_field_maps:
                    map_field_name = mapping["field_name"].strip()
                    column_name = mapping["column_name"].strip()

                    if (
                        map_field_name not in self.flat_fields.values()
                        and map_field_name not in self.actions
                    ):
                        continue  # Safely skip invalid mappings

                    elif map_field_name == self.Actions.SKIP.value:
                        df.drop(columns=column_name, inplace=True)

                        continue

                    field = self.serializer.get_flat_field(map_field_name)

                    if not field.is_list_item:
                        # Default field logic
                        df.rename(
                            columns={column_name: map_field_name},
                            inplace=True,
                        )
                        continue

                    #######################################################
                    # Handle list items.
                    #
                    # Mappings can come in as field[n].subfield, or field[0].subfield.
                    # If the mapping uses n for the index, then the n will be the "nth" occurance
                    # of that field, starting at 0.
                    #
                    # At this point, all "field" (FlatListField) values are index=None,
                    # n-mappings will all be assigned indexes.
                    #######################################################

                    # Determine type
                    numbers = re.findall(r"\d+", column_name)
                    assert len(numbers) <= 1, (
                        "List items can only contain 0 or 1 numbers (multi digit allowed)."
                    )

                    if len(numbers) == 1:
                        # Number was provided in spreadsheet
                        index = numbers[0]
                    else:
                        # Number was not provided in spreadsheet, get index of field
                        index = len(
                            [
                                key
                                for key in generic_list_keys
                                if key == field.generic_key
                            ]
                        )

                    field.set_index(index)
                    generic_list_keys.append(field.generic_key)

                    df.rename(columns={column_name: str(field)}, inplace=True)

            self._log_job_msg("Cleaning csv data and standardizing fields...")

            # Normalize & clean fields before conversion to dict
            for field_name, field_type in self.serializer.get_flat_fields().items():
                if field_name not in list(df.columns):
                    continue

                if field_type.is_list_item:
                    df[field_name] = df[field_name].map(
                        lambda val: [
                            (
                                (item for item in str_to_list(val) if str(item) != "")
                                if isinstance(val, str)
                                else val
                            )
                        ]
                    )
                else:
                    df[field_name] = df[field_name].map(
                        lambda val: val if val != "" else None
                    )

            # Convert df to list of dicts, drop null fields
            upload_data = df.to_dict("records")
            filtered_data = [
                {k: v for k, v in record.items() if v is not None}
                for record in upload_data
            ]

            # Finally, save data if valid
            success = []
            errors = []

            self._log_job_msg("Unflattening csv data...")

            # Note: string stripping is done in the serializer
            serializers = [
                self.serializer_class(data=data, flat=True) for data in filtered_data
            ]

            self._log_job_msg("Starting database update process...")

            for i, serializer in enumerate(serializers):
                if serializer.is_valid():
                    serializer.save()
                    success.append(serializer.data)
                else:
                    report = {**serializer.data, "errors": {**serializer.errors}}
                    errors.append(report)

                self._log_job_kwarg(key="processed", value=str(i + 1))

            if self.job:
                self.job.end_clock()

            return success, errors

        except Exception as e:
            print_error()
            return [], e
