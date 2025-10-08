import copy
from enum import Enum
from time import sleep

import requests
from django.contrib.auth.models import Permission
from django.core import validators
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from utils.helpers import get_full_url
from utils.permissions import get_perm_label, get_permission


class FieldType(Enum):
    READONLY = "readonly"
    WRITABLE = "writable"
    REQUIRED = "required"
    UNIQUE = "unique"
    LIST = "list"
    IMAGE = "image"
    BOOLEAN = "boolean"


class SerializerBase(serializers.Serializer):
    """Wrapper around the base drf serializer."""

    datetime_format = "%Y-%m-%d %H:%M:%S"

    @cached_property
    def all_fields(self) -> list[str]:
        """Get list of all fields in serializer."""

        return list(self.get_fields().keys())

    @cached_property
    def readable_fields(self) -> list[str]:
        """Get list of all fields in serializer that can be read."""

        return self.all_fields

    @cached_property
    def writable_fields(self) -> list[str]:
        """Get list of all fields that can be written to."""

        return [
            key for key, value in self.get_fields().items() if value.read_only is False
        ]

    @cached_property
    def readonly_fields(self) -> list[str]:
        """Get list of all fields that can only be read, not written."""

        return [
            key for key, value in self.get_fields().items() if value.read_only is True
        ]

    @cached_property
    def writeonly_fields(self) -> list[str]:
        """Get a list of all fields that can only be written to."""

        return [
            key for key, value in self.get_fields().items() if value.write_only is True
        ]

    @cached_property
    def required_fields(self) -> list[str]:
        """Get list of all fields that must be written to on object creation."""

        return [
            key
            for key, value in self.get_fields().items()
            if value.required is True and value.read_only is False
        ]

    @cached_property
    def optional_fields(self) -> list[str]:
        """Get list of all fields are not required for object creation."""

        return [
            key
            for key, value in self.get_fields().items()
            if value.required is False and value.read_only is False
        ]

    @cached_property
    def nullable_fields(self) -> list[str]:
        """Fields that might not be present on the read-only version of the serializer."""

        return [
            key for key, value in self.get_fields().items() if value.allow_null is True
        ]

    @cached_property
    def image_fields(self) -> list[str]:
        """List of fields that are of type ImageField."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.ImageField)
        ]

    @cached_property
    def boolean_fields(self) -> list[str]:
        """List of fields that are of type BooleanField."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.BooleanField)
        ]

    @cached_property
    def choice_fields(self) -> list[str]:
        """List of fields that have choices."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.ChoiceField)
        ]

    @cached_property
    def simple_fields(self) -> list[str]:
        """List of all fields that are not lists or nested objects."""

        exclude_fields = (
            self.many_related_fields
            + self.list_fields
            + self.nested_fields
            + self.many_nested_fields
        )

        return [
            field_name
            for field_name in self.all_fields
            if field_name not in exclude_fields
        ]

    @cached_property
    def simple_list_fields(self) -> list[str]:
        """List of all fields that are a list of a single flat value."""

        return list(
            set(
                [
                    key
                    for key, value in self.get_fields().items()
                    if isinstance(value, serializers.ListField)
                    # or getattr(value, "many", False)
                ]
                + self.many_related_fields
            )
        )

    @cached_property
    def many_related_fields(self) -> list[str]:
        """List of fields that inherit RelatedField, and are many=True."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.ManyRelatedField)
        ]

    @cached_property
    def list_fields(self) -> list[str]:
        """List of fields that represent a list of items."""

        return list(
            set(
                [
                    key
                    for key, value in self.get_fields().items()
                    if isinstance(value, serializers.ListField)
                    or getattr(value, "many", False)
                ]
                + self.many_related_fields
                + self.many_nested_fields
            )
        )

    @cached_property
    def nested_fields(self):
        """List of fields that are nested serializers."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.BaseSerializer)
            and not (hasattr(value, "many") and value.many)
        ]

    @cached_property
    def many_nested_fields(self):
        """List of fields that are nested serializers with many=True."""
        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.BaseSerializer)
            and (hasattr(value, "many") and value.many)
        ]

    @cached_property
    def all_nested_fields(self):
        """List of fields that are nested serializers, whether many=True or False."""

        return self.nested_fields + self.many_nested_fields

    def get_fields(self) -> dict[str, serializers.Field | serializers.BaseSerializer]:
        return super().get_fields()

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

        if field_name in serializer.boolean_fields:
            field_types.append(FieldType.BOOLEAN)

        return field_types


class ModelSerializerBase(SerializerBase, serializers.ModelSerializer):
    """Default functionality for model serializer."""

    datetime_format = SerializerBase.datetime_format

    default_fields = ["id", "created_at", "updated_at"]

    class Meta:
        model = None

    @property
    def model_class(self) -> type[models.Model]:
        return self.Meta.model

    @cached_property
    def pk_field(self) -> str | None:
        """Get the field name used as the primary key (usually id)."""

        for field in self.model_class._meta.get_fields():
            if getattr(field, "primary_key", False) and field.name in self.all_fields:
                return field.name

        return None
        # raise Exception(
        #     f"Model {self.model_class.__name__} does not have a primary key!"
        # )

    @cached_property
    def unique_fields(self) -> list[str]:
        """Get list of all fields that can be used to unique identify models."""

        model_fields = self.model_class._meta.get_fields()
        unique_fields = [
            field.name
            for field in model_fields
            if getattr(field, "primary_key", False) or getattr(field, "_unique", False)
        ]

        return [field for field in self.readable_fields if field in unique_fields]

    @cached_property
    def related_fields(self) -> list[str]:
        """List of fields that inherit RelatedField, representing foreign key relations."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.RelatedField)
        ]

    @cached_property
    def many_related_fields(self) -> list[str]:
        """List of fields that inherit ManyRelatedField, representing M2M relations."""

        return [
            key
            for key, value in self.get_fields().items()
            if isinstance(value, serializers.ManyRelatedField)
        ]

    @cached_property
    def any_related_fields(self) -> list[str]:
        """List of fields that are single or many related."""

        return self.related_fields + self.many_related_fields

    @cached_property
    def unique_together_fields(self):
        """List of tuples of fields that must be unique together."""

        constraints = self.model_class._meta.constraints

        return [
            constraint.fields
            for constraint in constraints
            if isinstance(constraint, models.UniqueConstraint)
        ]

    def run_prevalidation(self, data=None):
        """
        Can be used to pull out objects and set child querysets before actual validation.
        This can be used to scope querysets of certain fields to other fields.

        Example setting queryset of "child" field based on "parent":
        ```
        def run_pre_validation(self, data=None):
            children = data.pop('children', None)

            res = super().run_prevalidation(data)
            parent = res.get('parent')
            self.fields['children'].child_relation.queryset = Model.objects.filter(parent=parent)

            return res
        """
        return super().run_validation(data)

    def run_validation(self, data=None):
        pre_data = copy.deepcopy(data)
        self.run_prevalidation(pre_data)
        return super().run_validation(data)


class ModelSerializer(ModelSerializerBase):
    """Base fields for model serializer."""

    datetime_format = SerializerBase.datetime_format

    id = serializers.IntegerField(label="ID", read_only=True)
    created_at = serializers.DateTimeField(
        format=datetime_format, read_only=True, required=False
    )
    updated_at = serializers.DateTimeField(
        format=datetime_format, read_only=True, required=False
    )

    class Meta:
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class UpdateListSerializer(serializers.ListSerializer):
    # Ref: https://levelup.gitconnected.com/really-fast-bulk-updates-with-django-rest-framework-43594b18bd75
    def update(self, instances, validated_data):
        instance_hash = dict(enumerate(instances))

        result = [
            self.child.update(instance_hash[index], attrs)
            for index, attrs in enumerate(validated_data)
        ]

        return result


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
            return get_full_url(value.url)
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

        file_type = res.headers["Content-Type"]
        if not file_type or "/" not in file_type:
            raise Exception("Invalid file type:", file_type)

        file_type = file_type.split("/")[1]

        temp_file = NamedTemporaryFile(delete=True)
        temp_file.write(res.content)
        temp_file.flush()

        name = str(data.split("/")[-1])

        if not name.endswith(file_type):
            name += f".{file_type}"

        file = File(temp_file, name=name)

        validators.validate_image_file_extension(file)

        return file


@extend_schema_field(OpenApiTypes.STR)
class PermissionRelatedField(serializers.RelatedField):
    """Display permissions in JSON."""

    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", Permission.objects.all())

        super().__init__(**kwargs)

    def to_internal_value(self, data: str):
        return get_permission(data)

    def to_representation(self, obj: Permission):
        return get_perm_label(obj)
