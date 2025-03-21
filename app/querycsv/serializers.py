import re
import traceback
import uuid
from time import sleep
from typing import Iterable, Optional

import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.relations import SlugRelatedField
from rest_framework.utils import model_meta

from core.abstracts.serializers import FieldType, ModelSerializerBase, SerializerBase
from utils.helpers import str_to_list
from utils.types import islistinstance


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
    def image_url_fields(self):
        """List of fields that represent images."""

        return [
            key
            for key, value in self.get_fields().items()
            if (isinstance(value, ImageUrlField))
        ]

    @property
    def flat_data(self):
        """Like ``serializer.data``, but returns flattened data."""

        data = self.data
        return self.json_to_flat(data)

    @classmethod
    def json_to_flat(cls, data: dict):
        """Convert representation to flattened struction for CSV."""
        parsed = {}

        for key, value in data.items():
            # Convert lists to string
            if isinstance(value, list) and islistinstance(value, dict):
                for i, obj in enumerate(value):
                    parent_key = f"{key}[{i}]"

                    for nested_key, nested_value in obj.items():
                        if nested_value == "":
                            continue
                        final_key = ".".join([parent_key, nested_key])
                        parsed[final_key] = nested_value
            elif isinstance(value, list):
                parsed[key] = ", ".join(
                    [str(v) if "," not in str(v) else f'"{str(v)}"' for v in value]
                )
            # TODO: Flatten nested objects
            else:
                parsed[key] = value

        return parsed

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

        # For each field, convert flattened syntax to JSON representation
        for key, value in record.items():
            list_objs_res = re.match(r"([a-z0-9_-]+)\[([0-9]+)\]\.?(.*)?", key)
            nested_obj_res = re.match(r"([a-z0-9_-]+)\.(.*)", key)

            if key in cls().writable_many_related_fields and isinstance(value, str):
                # Handle list of slug related fields
                parsed[key] = str_to_list(value)
            elif key in cls().writable_many_related_fields and not isinstance(
                value, list
            ):
                # Handle slug related field
                parsed[key] = [value]
            elif bool(nested_obj_res):
                # Handle nested object

                main_field, nested_field = nested_obj_res.groups()
                assert (
                    main_field in cls().nested_fields
                ), f"Field {main_field} is not a nested object."

                # Create new nested object if not exists
                if main_field not in parsed.keys():
                    parsed[main_field] = {}

                # Set a single field on the nested object
                # FIXME: This will probably break on lists inside nested serializers
                parsed[main_field][nested_field] = value

            elif bool(list_objs_res):
                # Handle list of nested objects
                main_field, index, nested_field = list_objs_res.groups()
                index = int(index)

                assert (
                    main_field in cls().many_nested_fields
                ), f"Field {main_field} is not a list of nested objects."

                if main_field not in parsed.keys():
                    parsed[main_field] = []

                assert isinstance(
                    parsed[main_field], list
                ), f"Inconsistent types for field {main_field}"

                # Need to ensure the object is put at that specific location,
                # since the other fields will expect it there.
                while len(parsed[main_field]) <= index:
                    parsed[main_field].append({})

                # TODO: Recurse for deeply nested objects
                if value == "" or value is None:
                    continue
                parsed[main_field][index][nested_field] = value
            else:
                # Default
                if str(value).strip() == "":
                    continue

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

                flat_fields[nested_field_name] = field

        return flat_fields


class CsvModelSerializer(FlatSerializer, ModelSerializerBase):
    """Convert fields to csv columns."""

    def __init__(self, instance=None, data=empty, **kwargs):
        """Override default functionality to implement update or create."""

        # Skip if data is empty
        if data is None or data is empty:
            return super().__init__(instance=instance, **kwargs)

        # Try to expand out fields before processing
        data = self.flat_to_json(data)

        # Initialize rest of serializer first, needed if data is flat
        super().__init__(data=data, **kwargs)

        # Allow create_or_update functionality
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

    def _parse_m2m_value(self, value, field):
        """Parses m2m values for create/update methods."""

        if islistinstance(value, dict):
            model = field.model
            saved_objs = []

            for nested_obj in value:
                obj, _ = model._default_manager.get_or_create(**nested_obj)
                saved_objs.append(obj)

            value = saved_objs

        if not isinstance(value, Iterable):
            value = [value]

        return value

    def _get_remote_field_name(self, field_name):
        """Get the field name a foreign model uses to reference this object."""
        ModelClass = self.Meta.model

        # We need the name of the field on the foreign object
        # that connects to this object. To get that, we need to
        # find the info about this relationship by looping through
        # the related field descriptors and finding the correct one.
        # ModelClass._meta.related_objects returns list of ManyToOneRel or ManyToManyRel
        rel_obj = [
            rel for rel in ModelClass._meta.related_objects if rel.name == field_name
        ][0]

        # We'll have a ManyToOneRel/ManyToManyRel, which has a reference
        # to the field that connects to this model
        remote_name = rel_obj.remote_field.name

        return remote_name

    def _get_remote_model(self, field_name, info=None):
        """Get the model that is at the other end of a foreign relationship."""

        if info is None:
            ModelClass = self.Meta.model
            info = model_meta.get_field_info(ModelClass)

        return info.relations[field_name].related_model

    def _download_image(self, instance, field_name, url):
        """Given external url, download and save image to the instance."""

        res = requests.get(
            url,
            stream=True,
        )

        retries = 3
        while res.status_code > 300:
            if retries < 1:
                break

            sleep(3)

            res = requests.get(url, stream=True)
            retries = retries - 1

        if not res.status_code < 300:
            raise ValueError(
                f"Expected url {url} to return 200, but returned {res.status_code}"
            )

        temp_file = NamedTemporaryFile(delete=True)
        temp_file.write(res.content)
        temp_file.flush()

        file = File(temp_file, uuid.uuid4().__str__())
        setattr(instance, field_name, file)
        instance.save()

    def create(self, validated_data):
        """
        Override default create method.

        DRF does not like calling ``.create()`` on a serializer that has
        a nested serializer, so we just override the entire method.

        This code was adapted from the original DRF create method to include
        functionality to handle more complex model relationships.
        """

        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        reverse_many = {}

        for field_name, relation_info in info.relations.items():
            if (
                relation_info.to_many
                and (field_name in validated_data)
                and not relation_info.reverse
            ):
                # This model references foreign model via m2m
                many_to_many[field_name] = validated_data.pop(field_name)
            elif not relation_info.to_many and (field_name in validated_data):
                # This model references foreign model via fk
                payload = validated_data.pop(field_name, None)
                model = self._get_remote_model(field_name, info=info)

                if not payload:
                    continue
                elif not isinstance(payload, dict):
                    validated_data[field_name] = payload
                    continue

                validated_data[field_name], _ = model._default_manager.get_or_create(
                    **payload
                )
            elif (
                relation_info.to_many
                and relation_info.reverse
                and (field_name in validated_data)
            ):
                # Many to one reversed or many to many reversed
                # The foreign model either references this model via fk,
                # or the foreign model references this model via m2m
                payload = validated_data.pop(field_name, None)
                reverse_many[field_name] = payload

        # Handle images
        image_urls = {}
        for field_name in self.image_url_fields:
            data = validated_data.pop(field_name, None)

            if data is None:
                continue

            image_urls[field_name] = data

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
                value = self._parse_m2m_value(value, field)
                field.set(value)

        # Create foreign models that reference this model
        if reverse_many:
            for field_name, value in reverse_many.items():
                if not isinstance(value, list):
                    value = [value]

                remote_name = self._get_remote_field_name(field_name)
                remote_model = self._get_remote_model(field_name, info=info)

                for obj in value:
                    # Add this model to the payload for creating the foreign object
                    obj[remote_name] = instance
                    remote_model._default_manager.create(**obj)

        # Download images and save to model
        if image_urls:
            for field_name, url in image_urls.items():
                self._download_image(instance, field_name=field_name, url=url)

        return instance

    def update(self, instance, validated_data):
        """
        Override default update method.

        DRF does not like calling ``.udpate()`` on a serializer that has
        a nested serializer, so we just override the entire method.

        This code was adapted from the original DRF update method to include
        functionality to handle more complex model relationships.
        """
        info = model_meta.get_field_info(instance)

        image_urls = {}

        for field in self.image_url_fields:
            if field in validated_data:
                url = validated_data.pop(field, None)
                if url is None:
                    continue

                image_urls[field] = url

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        m2m_fields = []
        for attr, value in validated_data.items():
            if (
                attr in info.relations
                and info.relations[attr].to_many
                and not info.relations[attr].reverse
            ):
                # This model references foreign model via m2m
                m2m_fields.append((attr, value))
            elif attr in info.relations and not info.relations[attr].to_many:
                # This model references foreign model via fk
                if isinstance(value, dict):
                    model = info.relations[attr].related_model
                    value, _ = model._default_manager.get_or_create(**value)

                setattr(instance, attr, value)
            elif (
                attr in info.relations
                and info.relations[attr].to_many
                and info.relations[attr].reverse
            ):
                # Many to one reversed or many to many reversed
                # The foreign model either references this model via fk,
                # or the foreign model references this model via m2m
                remote_name = self._get_remote_field_name(attr)
                remote_model = self._get_remote_model(attr, info=info)

                if not isinstance(value, list):
                    value = [value]

                for obj in value:
                    # For each, set this instance as appropriate field, then create/skip
                    obj[remote_name] = instance
                    remote_model._default_manager.get_or_create(**obj)
            else:
                setattr(instance, attr, value)

        instance.save()

        # Note that many-to-many fields are set after updating instance.
        # Setting m2m fields triggers signals which could potentially change
        # updated instance and we do not want it to collide with .update()
        for attr, value in m2m_fields:
            field = getattr(instance, attr)
            value = self._parse_m2m_value(value, field)
            field.set(value)

        # Save any images
        for field_name, value in image_urls.items():
            current_image = getattr(instance, field_name, None)

            # This would happen if reuploading a csv, url would be the same
            if current_image and current_image.url == value:
                continue

            self._download_image(instance, field_name=field_name, url=value)

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


class ImageUrlField(serializers.URLField):
    """
    Represents an image via a url.

    Allows images to be uploaded to API via external urls.
    """
