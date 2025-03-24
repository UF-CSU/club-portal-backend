from enum import Enum
from time import sleep
from typing import Type

import requests
from django.core import validators
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class FieldType(Enum):
    READONLY = "readonly"
    WRITABLE = "writable"
    REQUIRED = "required"
    UNIQUE = "unique"
    LIST = "list"
    IMAGE = "image"


class SerializerBase(serializers.Serializer):
    """Wrapper around the base drf serializer."""

    datetime_format = "%Y-%m-%d %H:%M:%S"

    @property
    def all_fields(self) -> list[str]:
        """Get list of all fields in serializer."""

        return [key for key in self.get_fields().keys()]

    @property
    def readable_fields(self) -> list[str]:
        """Get list of all fields in serializer that can be read."""

        return self.all_fields

    @property
    def writable_fields(self) -> list[str]:
        """Get list of all fields that can be written to."""

        return [
            key for key, value in self.get_fields().items() if value.read_only is False
        ]

    @property
    def readonly_fields(self) -> list[str]:
        """Get list of all fields that can only be read, not written."""

        return [
            key for key, value in self.get_fields().items() if value.read_only is True
        ]

    @property
    def required_fields(self) -> list[str]:
        """Get list of all fields that must be written to on object creation."""

        return [
            key
            for key, value in self.fields.items()
            if value.required is True and value.read_only is False
        ]

    @property
    def image_fields(self) -> list[str]:
        """List of fields that are of type ImageField."""

        return [
            key
            for key, value in self.fields.items()
            if isinstance(value, serializers.ImageField)
        ]

    @property
    def many_related_fields(self) -> list[str]:
        """List of fields that inherit RelatedField, and are many=True."""

        return [
            key
            for key, value in self.fields.items()
            if isinstance(value, serializers.ManyRelatedField)
        ]

    @property
    def list_fields(self) -> list[str]:
        """List of fields that represent a list of items."""

        return list(
            set(
                [
                    key
                    for key, value in self.fields.items()
                    if isinstance(value, serializers.ListField)
                    or getattr(value, "many", False)
                ]
                + self.many_related_fields
                + self.many_nested_fields
            )
        )

    @property
    def nested_fields(self):
        """List of fields that are nested serializers."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.BaseSerializer)
            and not (hasattr(value, "many") and value.many)
        ]

    @property
    def many_nested_fields(self):
        """List of fields that are nested serializers with many=True."""
        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.BaseSerializer)
            and (hasattr(value, "many") and value.many)
        ]

    def get_field_types(self, field_name: str, serializer=None) -> list[FieldType]:
        """Get ``FieldType`` for a given field."""
        serializer = serializer if serializer is not None else self

        field_types = []

        if field_name in serializer.writable_fields:
            field_types.append(FieldType.WRITABLE)

        if field_name in serializer.readonly_fields:
            field_types.append(FieldType.READONLY)

        if field_name in serializer.required_fields:
            field_types.append(FieldType.REQUIRED)

        if field_name in serializer.unique_fields:
            field_types.append(FieldType.UNIQUE)

        if field_name in serializer.list_fields:
            field_types.append(FieldType.LIST)

        if field_name in serializer.image_fields:
            field_types.append(FieldType.IMAGE)

        return field_types


class ModelSerializerBase(serializers.ModelSerializer):
    """Default functionality for model serializer."""

    datetime_format = SerializerBase.datetime_format

    id = serializers.IntegerField(label="ID", read_only=True)
    created_at = serializers.DateTimeField(
        format=datetime_format, read_only=True, required=False, allow_null=True
    )
    updated_at = serializers.DateTimeField(
        format=datetime_format, read_only=True, required=False, allow_null=True
    )

    default_fields = ["id", "created_at", "updated_at"]

    class Meta:
        model = None

    @property
    def model_class(self) -> Type[models.Model]:
        return self.Meta.model

    @property
    def unique_fields(self) -> list[str]:
        """Get list of all fields that can be used to unique identify models."""

        model_fields = self.model_class._meta.get_fields()
        unique_fields = [
            field
            for field in model_fields
            if getattr(field, "primary_key", False) or getattr(field, "_unique", False)
        ]
        unique_fields = [field.name for field in unique_fields]

        return [field for field in self.readable_fields if field in unique_fields]

    @property
    def related_fields(self) -> list[str]:
        """List of fields that inherit RelatedField, representing foreign key relations."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.RelatedField)
        ]

    @property
    def many_related_fields(self) -> list[str]:
        """List of fields that inherit ManyRelatedField, representing M2M relations."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.ManyRelatedField)
        ]

    @property
    def any_related_fields(self) -> list[str]:
        """List of fields that are single or many related."""

        return self.related_fields + self.many_related_fields

    @property
    def unique_together_fields(self):
        """List of tuples of fields that must be unique together."""

        constraints = self.model_class._meta.constraints

        return [
            constraint.fields
            for constraint in constraints
            if isinstance(constraint, models.UniqueConstraint)
        ]


class ModelSerializer(ModelSerializerBase):
    """Base fields for model serializer."""

    class Meta:
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class StringListField(serializers.CharField):
    """Represent a comma-separated string as a list of strings."""

    def to_representation(self, value: str):
        """Convert to list for json."""

        return value.split(",")

    def to_internal_value(self, data):
        """Convert to string for database."""

        if isinstance(data, list):
            return ",".join(data)

        return data


class ImageUrlField(serializers.Field):
    """
    Represents an image via a url.

    Allows images to be uploaded to API via external urls.
    """

    default_error_messages = {"invalid_url": _("Enter a valid URL.")}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_validator = validators.URLValidator(
            message=self.error_messages["invalid_url"]
        )
        # url_validator = URLValidator(message=self.error_messages["invalid_url"])
        # image_validator = validators.validate_image_file_extension

        # self.validators.append(url_validator)
        # self.validators.append(image_validator)

    def to_representation(self, value):
        try:
            return value.url
        except Exception:
            return None

    def to_internal_value(self, data):
        self.url_validator(data)

        res = requests.get(
            data,
            stream=True,
        )

        retries = 3
        while res.status_code > 300:
            if retries < 1:
                break

            sleep(2)

            res = requests.get(data, stream=True)
            retries = retries - 1

        if not res.status_code < 300:
            raise ValueError(
                f"Expected url {data} to return 200, but returned {res.status_code}"
            )

        temp_file = NamedTemporaryFile(delete=True)
        temp_file.write(res.content)
        temp_file.flush()

        name = data.split("/")[-1]
        file = File(temp_file, name=name)

        validators.validate_image_file_extension(file)

        return file


image_serializer = serializers.ImageField, serializers.URLField
