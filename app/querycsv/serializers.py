import re
import traceback
from collections.abc import Iterable
from typing import Optional

from django.db import models
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.relations import SlugRelatedField
from rest_framework.utils import model_meta

from core.abstracts.serializers import FieldType, ModelSerializerBase, SerializerBase
from utils.helpers import str_to_bool, str_to_list
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
        self.field_instance = value

    def __str__(self):
        return self.key

    def __eq__(self, value):
        return self.key == value

    @property
    def __name__(self):
        return "FlatField"

    def __repr__(self):
        return f"<{self.__name__}: key={self.__str__()},  types={','.join([str(t) for t in self.field_types])}>"

    def parse_value(self, value):
        """Given a raw value, will parse and return the current format."""

        if FieldType.LIST in self.field_types and not isinstance(value, list):
            return str_to_list(value)
        elif FieldType.BOOLEAN in self.field_types:
            return str_to_bool(value)
        elif isinstance(value, str) and value.isdigit():
            return int(value)
        elif isinstance(self.field_instance, serializers.IntegerField) and (
            str(value).strip() != ""
        ):
            # Pandas usually returns floats inside strings, massage this to int
            return int(float(value))

        return value

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

    list_pattern = r"\[(\d+|n)\]"
    """Selects all instances of square bracket syntax for lists."""

    def __init__(self, key, value, field_types):
        super().__init__(key, value, field_types)

        self._set_list_values()

    @property
    def __name__(self):
        return "FlatListField"

    def __eq__(self, value):
        return value == self.key or re.sub(self.list_pattern, "[n]", value) == self.key

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
    def many_related_fields(self):
        return super().many_related_fields + self.writable_many_related_fields

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

            if getattr(value, "many", False):
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

    def get_flat_field(self, field_name: str):
        """
        Pass in field names, starting with outermost parent, to get
        structured representation.
        """

        flat_fields = self.get_flat_fields()

        for field in flat_fields.values():
            if field_name == field:  # Compares string values, returns class
                return field

        return None

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
        self = cls()

        # For each field, convert flattened syntax to JSON representation
        for key, value in record.items():
            # For listed objects, n-mappings must be already converted to numbers
            list_objs_res = re.match(r"([a-z0-9_-]+)\[([0-9]+)\]\.?(.*)?", key)
            nested_obj_res = re.match(r"([a-z0-9_-]+)\.(.*)", key)

            field = self.get_flat_field(key)

            if field is not None:
                value = field.parse_value(value)

            if bool(nested_obj_res):
                # Handle nested object

                main_field, nested_field = nested_obj_res.groups()
                assert main_field in self.nested_fields, (
                    f"Field {main_field} is not a nested object."
                )

                # Create new nested object if not exists
                if main_field not in parsed.keys():
                    parsed[main_field] = {}

                if value is None:
                    continue

                # Set a single field on the nested object
                parsed[main_field][nested_field] = value

            elif bool(list_objs_res):
                # Handle list of nested objects
                main_field, index, nested_field = list_objs_res.groups()
                index = int(index)

                assert main_field in self.many_nested_fields, (
                    f"Field {main_field} is not a list of nested objects {self.many_nested_fields}."
                )

                if main_field not in parsed.keys():
                    parsed[main_field] = []

                assert isinstance(parsed[main_field], list), (
                    f"Inconsistent types for field {main_field}"
                )

                # Need to ensure the object is put at that specific location,
                # since the other fields will expect it there.
                while len(parsed[main_field]) <= index:
                    parsed[main_field].append({})

                if (
                    value == ""
                    or value is None
                    or (isinstance(value, list) and len(value) == 0)
                ):
                    continue

                # TODO: Recurse for deeply nested objects
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


class CsvModelSerializer(FlatSerializer, ModelSerializerBase):
    """Convert fields to csv columns."""

    def __init__(self, instance=None, data=empty, **kwargs):
        """Override default functionality to implement update or create."""

        # Skip if data is empty
        if data is None or data is empty:
            return super().__init__(instance=instance, **kwargs)

        # Try to expand out fields before processing
        data = self.flat_to_json(data)

        # Then initialize rest of serializer
        super().__init__(data=data, **kwargs)

    def initialize_instance(self, data=empty) -> None:
        """
        Set self.instance using data.

        Allow create_or_update functionality by searching for existing models
        with the same unique fields. By default, the serializer would fail
        at the validation stage if an instance exists, but this allows the
        serialzier to select that instance for update instead.
        """

        if data is empty or not data or self.instance is not None:
            return

        try:
            ModelClass = self.model_class
            search_query = None

            # Check pk if pk value exists, short circuiting if it does
            pk_value = data.get(self.pk_field, None)
            if pk_value is not None:
                self.instance = ModelClass.objects.get(id=pk_value)
                return

            unique_data_fields = [
                field for field in self.unique_fields if field in data.keys()
            ]

            # Find object containing all unique fields (AND)
            for field in self.unique_fields:
                value = data.get(field, None)

                # Remove leading/trailing spaces before processing
                if value is None or value == "":
                    continue
                elif isinstance(value, str):
                    value = value.strip()

                # The value must exist and match
                query = models.Q(**{f"{field}__exact": value})

                # Allow updating unique fields if not set, but only if
                # there's another unique field to use as a lookup
                if field not in self.required_fields and len(unique_data_fields) > 1:
                    query = query | models.Q(**{f"{field}": None})

                if search_query is None:
                    search_query = query
                else:
                    search_query = search_query & query

            # Find object containing all sets of unique_together fields (AND)
            # FIXME: This will probably break for fields greater than 2
            for field_1, field_2 in self.unique_together_fields:
                values = {
                    field_1: data.get(field_1, None),
                    field_2: data.get(field_2, None),
                }

                for f in [field_1, field_2]:
                    value = values[f]

                    # Remove leading/trailing spaces before processing
                    if value is None or value == "":
                        continue
                    elif isinstance(value, str):
                        value = value.strip()

                    if f in self.related_fields:
                        values[f] = self.get_fields()[f].to_internal_value(values[f])

                # TODO: Test query functionality
                query_all_fields = models.Q(**{field_1: values[field_1]}) & models.Q(
                    **{field_2: values[field_2]}
                )
                query_field_1 = models.Q(**{field_1: values[field_1]}) & models.Q(
                    **{field_2: None}
                )
                query_field_2 = models.Q(**{field_1: None}) & models.Q(
                    **{field_2: values[field_2]}
                )
                query_no_fields = models.Q(**{field_1: None}) & models.Q(
                    **{field_2: None}
                )

                query = (
                    query_all_fields | query_field_1 | query_field_2 | query_no_fields
                )

                if search_query is None:
                    search_query = query
                else:
                    search_query = search_query & query

            query = ModelClass.objects.filter(search_query)
            if query.exists():
                self.instance = query.first()

        except Exception:
            pass

    def to_internal_value(self, data):
        # Why run initialization here?
        # This is one of the internal methods that is called first when running
        # `.is_valid()`, so this fixes any uniqueness issues that would have otherwise
        # have been raised by the validators.

        self.initialize_instance(data)
        return super().to_internal_value(data)

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
        reverse_one = {}

        # TODO: Save nested serializers, pass parent if a child serializer
        for field_name, relation_info in info.relations.items():
            if (
                relation_info.to_many
                and (field_name in validated_data)
                and not relation_info.reverse
            ):
                # This model references foreign model via m2m
                many_to_many[field_name] = validated_data.pop(field_name)
            elif (
                not relation_info.to_many
                and (field_name in validated_data)
                and not relation_info.reverse
            ):
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
                not relation_info.to_many
                and (field_name in validated_data)
                and relation_info.reverse
            ):
                # Foreign model references this model as one to one
                payload = validated_data.pop(field_name, None)
                reverse_one[field_name] = payload

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

        try:
            instance = ModelClass._default_manager.create(**validated_data)
        except TypeError as e:
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
            raise TypeError(msg) from e

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                value = self._parse_m2m_value(value, field)
                field.set(value)

        # Create foreign models that reference this model as many-to-one
        if reverse_many:
            for field_name, value in reverse_many.items():
                if not isinstance(value, list):
                    value = [value]

                remote_field = self._get_remote_field_name(field_name)
                remote_model = self._get_remote_model(field_name, info=info)

                for obj in value:
                    # Add this model to the payload for creating the foreign object
                    obj[remote_field] = instance
                    search = {remote_field: instance}

                    for key, value in obj.items():
                        # Add fields to search if they are not many-to-many
                        if not isinstance(value, list):
                            search[key] = value

                    remote_model._default_manager.update_or_create(
                        **search, defaults=obj
                    )

        # Create foreign models that reference this model as one-to-one
        if reverse_one:
            for (
                field_name,
                payload,
            ) in reverse_one.items():
                remote_field = self._get_remote_field_name(field_name)
                remote_model = self._get_remote_model(field_name, info=info)
                payload[remote_field] = instance

                # Fields to search for existing object
                search = {remote_field: instance}

                # Use search fields to find/create instance, payload to update fields either way
                remote_model._default_manager.update_or_create(
                    **search, defaults=payload
                )

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

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        m2m_fields = []

        for attr, value in validated_data.items():
            if attr not in info.relations:
                setattr(instance, attr, value)
                continue

            relation_info = info.relations[attr]

            if relation_info.to_many and not info.relations[attr].reverse:
                # This model references foreign model via m2m
                m2m_fields.append((attr, value))
            elif relation_info.to_many and relation_info.reverse:
                # Many to one reversed or many to many reversed
                # The foreign model either references this model via fk,
                # or the foreign model references this model via m2m
                remote_name = self._get_remote_field_name(attr)
                remote_model = self._get_remote_model(attr, info=info)

                if not isinstance(value, list):
                    value = [value]

                for obj in value:
                    # For each, either create or update an instance
                    obj[remote_name] = instance
                    search = {remote_name: instance}

                    for key, value in obj.items():
                        # Add fields to search if they are not many-to-many
                        if not isinstance(value, list):
                            search[key] = value

                    remote_model._default_manager.update_or_create(
                        **search, defaults=obj
                    )

            elif not relation_info.to_many and not relation_info.reverse:
                # This model references foreign model via fk
                if isinstance(value, dict):
                    model = info.relations[attr].related_model
                    value, _ = model._default_manager.get_or_create(**value)

                setattr(instance, attr, value)
            elif not relation_info.to_many and relation_info.reverse:
                # Foreign model references this model as one to one
                payload = validated_data.get(attr, None)

                remote_field = self._get_remote_field_name(attr)
                remote_model = self._get_remote_model(attr, info=info)
                payload[remote_field] = instance

                # Fields to search for existing object
                search = {remote_field: instance}

                # Use search fields to find/create instance, payload to update fields either way
                remote_model._default_manager.update_or_create(
                    **search, defaults=payload
                )
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
