import re
from enum import Enum
from typing import Literal, Optional, OrderedDict, Type, TypedDict

import pandas as pd
from django.db import models

from core.abstracts.serializers import ModelSerializerBase
from lib.spreadsheets import read_spreadsheet
from querycsv.consts import QUERYCSV_MEDIA_SUBDIR
from querycsv.models import QueryCsvUploadJob
from querycsv.serializers import CsvModelSerializer
from utils.files import get_media_path


class FieldMappingType(TypedDict):
    column_name: str
    field_name: str


class QueryCsvService:
    """Handle uploads and downloads of models using csvs."""

    class Actions(Enum):
        SKIP = "SKIP"
        CF = "CUSTOM_FIELD"

    def __init__(self, serializer_class: Type[CsvModelSerializer]):
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

    @classmethod
    def upload_from_job(cls, job: QueryCsvUploadJob):
        """Upload csv using predefined job."""

        assert job.serializer is not None, "Upload job must container serializer."

        svc = cls(serializer_class=job.serializer_class)
        return svc.upload_csv(job.file, custom_field_maps=job.custom_fields)

    @classmethod
    def queryset_to_csv(
        cls, queryset: models.QuerySet, serializer_class: Type[ModelSerializerBase]
    ):
        """Print a queryset to a csv, return file path."""

        service = cls(serializer_class=serializer_class)
        return service.download_csv(queryset)

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

        # Start by importing csv
        df = read_spreadsheet(path)

        # Update df values with header associations
        if custom_field_maps:
            generic_list_keys = []  # Used for determining index when ambiguous

            for mapping in custom_field_maps:
                map_field_name = mapping["field_name"]

                if (
                    map_field_name not in self.flat_fields.keys()
                    and map_field_name not in self.actions
                ):
                    continue  # Safely skip invalid mappings

                field = self.flat_fields[map_field_name]

                if not field.is_list_item:
                    # Default field logic
                    df.rename(
                        columns={mapping["column_name"]: map_field_name},
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
                numbers = re.findall(r"\d+", mapping["column_name"])
                assert (
                    len(numbers) <= 1
                ), "List items can only contain 0 or 1 numbers (multi digit allowed)."

                if len(numbers) == 1:
                    # Number was provided in spreadsheet
                    index = numbers[0]
                else:
                    # Number was not provided in spreadsheet, get index of field
                    index = len(
                        [key for key in generic_list_keys if key == field.generic_key]
                    )

                field.set_index(index)
                generic_list_keys.append(field.generic_key)

                df.rename(columns={mapping["column_name"]: str(field)}, inplace=True)

        # Normalize & clean fields before conversion to dict
        for field_name, field_type in self.serializer.get_flat_fields().items():
            if field_name not in list(df.columns):
                continue

            if field_type.is_list_item:
                df[field_name] = df[field_name].map(
                    lambda val: [
                        item for item in str(val).split(",") if str(item) != ""
                    ]
                )
            else:
                df[field_name] = df[field_name].map(
                    lambda val: val if val != "" else None
                )

        # Convert df to list of dicts, drop null fields
        upload_data = df.to_dict("records")
        filtered_data = [
            {k: v for k, v in record.items() if v is not None} for record in upload_data
        ]

        # Finally, save data if valid
        success = []
        errors = []

        # Note: string stripping is done in the serializer
        serializers = [
            self.serializer_class(data=data, flat=True) for data in filtered_data
        ]

        for serializer in serializers:
            if serializer.is_valid():
                serializer.save()
                success.append(serializer.data)
            else:
                report = {**serializer.data, "errors": {**serializer.errors}}
                errors.append(report)

        return success, errors
