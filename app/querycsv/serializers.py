import re
import traceback
from typing import Optional

from django.db import models
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.relations import SlugRelatedField
from rest_framework.utils import model_meta

from core.abstracts.serializers import FieldType, ModelSerializerBase, SerializerBase
from utils.helpers import str_to_list


class FlatField:
    key: str
    help_text: str
    field_types: list[FieldType]
    is_list_item = False

    def __init__(
        self, key: str, value: serializers.Field, field_types: list[FieldType]
    ):
        """Initialize field object, value is from serializer.get_fields[key]"""

        self.key = key
        self.help_text = value.help_text
        self.field_types = field_types

    def __str__(self):
        return self.key

    def __eq__(self, value):
        return self.key == value

    @property
    def is_readonly(self):
        return FieldType.READONLY in self.field_types

    @property
    def is_writable(self):
        return FieldType.WRITABLE in self.field_types

    @property
    def is_required(self):
        return FieldType.REQUIRED in self.field_types

    @property
    def is_unique(self):
        return FieldType.UNIQUE in self.field_types


class FlatListField(FlatField):
    """Represents a flat field that's part of a list."""

    is_list_item = True

    # Additional fields for list items
    index: Optional[int]
    parent_key: str
    sub_key: Optional[str]
    generic_key: str

    def __init__(self, key, value, field_types):
        super().__init__(key, value, field_types)

        self._set_list_values()

    def __eq__(self, value):
        return value == self.key or re.sub(r"\[(\d+|n)\]", "[n]", value) == self.key

    def _set_list_values(self):
        matches = re.match(r"([a-z0-9_-]+)\[(\d+|n)\]\.?(.*)?", self.key)
        assert bool(matches), f"Invalid list item field: {self.key}"

        parent_field, index, sub_field = list(matches.groups())

        self.parent_key = parent_field
        self.index = index if index != "n" else None
        self.sub_key = sub_field if sub_field != "" else None
        self.generic_key = re.sub(r"\[\d+|n\]", "[n]", self.key)

    def set_index(self, index: int):
        """Used when index is found later."""

        self.index = index
        self.key = f"{self.parent_key}[{index}]"

        if self.sub_key is not None:
            self.key += f".{self.sub_key}"


class FlatSerializer(SerializerBase):
    """Convert between json data and flattened data."""

    def __init__(self, instance=None, data=empty, flat=False, **kwargs):
        if not flat or not data:
            return super().__init__(instance, data, **kwargs)

        nested_data = self.flat_to_json(data)

        super().__init__(instance, data=nested_data, **kwargs)

    ##############################
    # == Serializer Functions == #
    ##############################

    @property
    def writable_many_related_fields(self):
        """List of fields that are WritableRelated, and have many=True"""

        return [
            key
            for key, value in self.get_fields().items()
            if (
                isinstance(value, serializers.ManyRelatedField)
                and isinstance(value.child_relation, WritableSlugRelatedField)
            )
            or (
                isinstance(value, serializers.ManyRelatedField)
                and value.read_only is False
            )
        ]

    @property
    def flat_data(self):
        """Like ``serializer.data``, but returns flattened data."""

        data = self.data
        return self.json_to_flat(data)

    @classmethod
    def json_to_flat(cls, data: dict):
        """Convert representation to flattened struction for CSV."""

        # TODO: Handle nested json to flat
        for key, value in data.items():
            # Convert lists to string
            if isinstance(value, list):
                data[key] = ", ".join([str(v) for v in value])

        return data

    @classmethod
    def flat_to_json(cls, record: dict) -> dict:
        """
        Convert data from csv to a nested json rep.

        Examples
        --------
        IN : {"some_list[0]": "zero", "some_list[1]": "one"}
        OUT: {"some_list": ["zero", "one"]}
        --
        IN : {"another_list[0].first_name": "John", "another_list[0].last_name": "Doe"}
        OUT: {"another_list": [{"first_name": "John", "last_name": "Doe"}]}
        """

        parsed = {}

        # Initial parsing
        for key, value in record.items():
            list_objs_res = re.match(r"([a-z0-9_-]+)\[([0-9]+)\]\.?(.*)?", key)

            if bool(list_objs_res):
                # Handle list of objects
                field, index, nested_field = list_objs_res.groups()
                index = int(index)

                if field not in parsed.keys():
                    parsed[field] = []

                assert isinstance(
                    parsed[field], list
                ), f"Inconsistent types for field {field}"

                # Need to ensure the object is put at that specific location,
                # since the other fields will expect it there.
                while len(parsed[field]) <= index:
                    parsed[field].append({})

                # TODO: Recurse for deeply nested objects
                parsed[field][index][nested_field] = value
            elif key in cls().writable_many_related_fields and isinstance(value, str):
                # Handle list of slug related fields
                parsed[key] = str_to_list(value)
            elif key in cls().writable_many_related_fields and not isinstance(
                value, list
            ):
                # Handle slug related field
                parsed[key] = [value]
            elif key in cls().nested_fields:
                # Handle nested object
                pass
            elif key in cls().many_nested_fields:
                # Handle list of nested objects
                pass
            else:
                # Default
                parsed[key] = value

        # Filtering
        for key, value in parsed.items():
            # Skip if: 1) not a list 2) empty list 3) list contains non-dict values
            if (
                not isinstance(value, list)
                or len(value) == 0
                or not isinstance(value[0], dict)
            ):
                continue

            # Remove empty objects from nested lists
            parsed[key] = [item for item in value if len(item.keys()) > 0]

        return parsed

    def get_flat_fields(self) -> dict[str, FlatField | FlatListField]:
        """Like ``get_fields``, returns a dict of fields with their flat type."""

        flat_fields = {}

        for key, value in self.get_fields().items():
            # For simple fields, just get FlatField value
            if not isinstance(value, serializers.BaseSerializer):

                field = FlatField(key, value, self.get_field_types(key))
                flat_fields[key] = field
                continue

            # For nested fields, add the inner fields using nested syntax
            field_name = key
            flat_field_class = None

            if hasattr(value, "many") and value.many:
                field_name += "[n]."
                sub_serializer = value.child
                flat_field_class = FlatListField
            else:
                field_name += "."
                sub_serializer = value
                flat_field_class = FlatField

            for sub_field in sub_serializer.get_fields():
                nested_field_name = field_name + sub_field

                field = flat_field_class(
                    nested_field_name,
                    sub_serializer.get_fields()[sub_field],
                    self.get_field_types(sub_field, serializer=sub_serializer),
                )

                flat_fields[key] = field

        return flat_fields


class CsvModelSerializer(FlatSerializer, ModelSerializerBase):
    """Convert fields to csv columns."""

    def __init__(self, instance=None, data=empty, **kwargs):
        """Override default functionality to implement update or create."""

        # Skip if data is empty
        if data is None:
            return super().__init__(instance=instance, **kwargs)

        # Try to expand out fields before processing
        try:
            data = self.flat_to_json(data)
        except Exception:
            pass

        # Initialize rest of serializer first, needed if data is flat
        super().__init__(data=data, **kwargs)

        # Allow create_or_udpate functionality
        try:
            if instance is None and data is not None and data is not empty:
                ModelClass = self.model_class
                search_fields = {}
                search_query = None

                for field in self.unique_fields:
                    value = data.get(field, None)

                    # Remove leading/trailing spaces before processing
                    if value is None or value == "":
                        continue
                    elif isinstance(value, str):
                        value = value.strip()

                    search_fields[field] = value

                    if search_query is None:
                        search_query = models.Q(**{field: value})
                    else:
                        search_query = search_query | models.Q(**{field: value})

                query = ModelClass.objects.filter(search_query)
                if query.exists():
                    instance = query.first()
            else:
                self.instance = instance

        except Exception:
            pass

        self.instance = instance

    def create(self, validated_data):
        """
        Override default create method.

        DRF does not like calling ``.create()`` on a serializer that has
        a nested serializer, so we just override the entire method.
        """
        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            instance = ModelClass._default_manager.create(**validated_data)
        except TypeError:
            tb = traceback.format_exc()
            msg = (
                "Got a `TypeError` when calling `%s.%s.create()`. "
                "This may be because you have a writable field on the "
                "serializer class that is not a valid argument to "
                "`%s.%s.create()`. You may need to make the field "
                "read-only, or override the %s.create() method to handle "
                "this correctly.\nOriginal exception was:\n %s"
                % (
                    ModelClass.__name__,
                    ModelClass._default_manager.name,
                    ModelClass.__name__,
                    ModelClass._default_manager.name,
                    self.__class__.__name__,
                    tb,
                )
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                field.set(value)

        return instance

    def update(self, instance, validated_data):
        """
        Override default update method.

        DRF does not like calling ``.udpate()`` on a serializer that has
        a nested serializer, so we just override the entire method.
        """
        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        m2m_fields = []
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                m2m_fields.append((attr, value))
            else:
                setattr(instance, attr, value)

        instance.save()

        # Note that many-to-many fields are set after updating instance.
        # Setting m2m fields triggers signals which could potentially change
        # updated instance and we do not want it to collide with .update()
        for attr, value in m2m_fields:
            field = getattr(instance, attr)
            field.set(value)

        return instance


class WritableSlugRelatedField(SlugRelatedField):
    """
    Wraps slug related field and creates object if not found.

    Optionally, provide ``extra_kwargs`` to add extra fields when
    an object is retrieved or created.
    """

    def __init__(self, slug_field=None, extra_kwargs=None, **kwargs):
        super().__init__(slug_field, **kwargs)

        self.extra_kwargs = extra_kwargs or {}

    def to_internal_value(self, data):
        """Overrides default behavior to create if not found."""
        queryset = self.get_queryset()

        try:
            obj, _ = queryset.get_or_create(
                **{self.slug_field: data}, **self.extra_kwargs
            )
            return obj
        except (TypeError, ValueError) as e:
            print(e)
