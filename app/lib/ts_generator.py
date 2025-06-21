import os
import typing
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Type
from uuid import UUID

from rest_framework import serializers

from core.abstracts.serializers import ModelSerializerBase, SerializerBase

DRF_FIELD_TYPES = {
    serializers.IntegerField: "number",
    serializers.BooleanField: "boolean",
    serializers.CharField: "string",
    serializers.DateField: "string",
    serializers.DateTimeField: "string",
    serializers.DecimalField: "number",
    serializers.DurationField: "string",
    serializers.EmailField: "string",
    serializers.ModelField: "any",
    serializers.FileField: "string",
    serializers.FloatField: "number",
    serializers.ImageField: "string",
    serializers.SlugField: "any",
    serializers.TimeField: "string",
    serializers.URLField: "string",
    serializers.UUIDField: "string",
    serializers.IPAddressField: "string",
    serializers.FilePathField: "string",
    serializers.PrimaryKeyRelatedField: "number",
}

PYTHON_TYPES = {
    str: "string",
    float: "number",
    bool: "boolean",
    bytes: "any",
    int: "number",
    UUID: "string",
    Decimal: "number",
    datetime: "string",
    date: "string",
    time: "string",
    timedelta: "string",
    IPv4Address: "string",
    IPv6Address: "string",
    dict: "any",
    typing.Any: "any",
    None: "unknown",
}

INTERFACE_TPL = """
/**
 * %(doc)s
 */
declare interface I%(model)s {
"""

CREATE_INTERFACE_TPL = """
/**
 * Fields needed to create %(article)s %(model)s object.
 *
 * @see {@link I%(model)s}
 */
declare interface I%(model)sCreate {
"""

UPDATE_INTERFACE_TPL = """
/**
 * Fields that can be updated for %(article)s %(model)s object.
 *
 * @see {@link I%(model)s}
 */
declare interface I%(model)sUpdate {
"""

FIELD_TPL = "  %(property)s: %(type)s;\n"
OPTIONAL_FIELD_TPL = "  %(property)s?: %(type)s;\n"
READONLY_FIELD_TPL = "  readonly %(property)s: %(type)s;\n"

FIELD_DOC_TPL = "\n  /** %s */\n"


class TypeGenerator:
    """Create TypeScript interfaces from a list of serializers."""

    def __init__(self, serializer_classes: list[Type[ModelSerializerBase]]):

        self.types_doc = ""
        self.serializer_classes = serializer_classes

    def _get_model_article(self, model_name: str):
        """Get a/an depending on a model's name."""

        return (
            "an"
            if model_name.lower().startswith(
                (
                    "a",
                    "e",
                    "i",
                    "o",
                )
            )
            else "a"
        )

    def _get_field_type(self, field, is_list=False):
        """Return TS type for given field."""

        field_type = DRF_FIELD_TYPES.get(type(field), None) or "any"

        if is_list:
            field_type += "[]"

        return field_type

    def _generate_field(
        self, tpl: str, property: str, field_type: str, doc: Optional[str] = None
    ):
        """Generate a TS field depending on tpl value."""

        generated = ""

        if doc:
            generated += FIELD_DOC_TPL % (doc,)

        generated += tpl % {
            "property": property,
            "type": field_type,
        }

        return generated

    def _generate_required_field(
        self, property: str, field_type: str, doc: Optional[str] = None
    ):
        """Generate a required TS field."""

        return self._generate_field(FIELD_TPL, property, field_type, doc=doc)

    def _generate_optional_field(
        self, property: str, field_type: str, doc: Optional[str] = None
    ):
        """Generate a optional TS field."""

        return self._generate_field(OPTIONAL_FIELD_TPL, property, field_type, doc=doc)

    def _generate_readonly_field(
        self, property: str, field_type: str, doc: Optional[str] = None
    ):
        """Generate a readonly TS field."""

        return self._generate_field(READONLY_FIELD_TPL, property, field_type, doc=doc)

    def _generate_fields(
        self,
        serializer: SerializerBase,
        all_optional=False,
        skip_readonly=False,
        skip_pk=True,
        allow_null=False,
        indent_level=0,
    ):
        """Generate a list of fields for given serializer."""

        all_fields = serializer.get_fields()
        properties = []
        indent = "  " * indent_level

        def gen_field(field_name, field_type=None, required=True, readonly=False):
            field = all_fields[field_name]
            field_type = field_type or self._get_field_type(field)

            if not readonly and not allow_null and not field.allow_null:
                field_prop = self._generate_required_field(field_name, field_type)
            elif not readonly and (all_optional or not required):
                field_prop = self._generate_optional_field(field_name, field_type)
            elif not readonly:
                field_prop = self._generate_required_field(field_name, field_type)
            else:
                field_prop = self._generate_readonly_field(field_name, field_type)

            return indent + field_prop

        # Generate required fields
        for field_name in serializer.required_fields:
            if field_name not in serializer.simple_fields:
                continue

            field_prop = gen_field(field_name, required=True)
            properties.append(field_prop)

        # Generate optional fields
        for field_name in serializer.optional_fields:
            if field_name not in serializer.simple_fields:
                continue

            field_prop = gen_field(field_name, required=False)
            properties.append(field_prop)

        # Generate single value list fields
        for field_name in serializer.simple_list_fields:
            field = all_fields[field_name]

            if isinstance(field, serializers.ManyRelatedField):
                field_type = self._get_field_type(field.child_relation, is_list=True)
            elif getattr(field, "child", None) is not None:
                field_type = self._get_field_type(field.child, is_list=True)
            else:
                field_type = "string[]"

            field_prop = gen_field(
                field_name,
                field_type=field_type,
                required=(field_name in serializer.required_fields),
            )
            properties.append(field_prop)

        # Generate nested fields
        for field_name in serializer.nested_fields:
            field = all_fields[field_name]

            nested_properties = self._generate_fields(
                field,
                all_optional=all_optional,
                indent_level=indent_level + 1,
            )

            # Skip fields with no properties
            if len(nested_properties) < 1:
                continue

            if field_name in serializer.required_fields and not all_optional:
                properties.append(indent + "  %s: {\n" % (field_name,))
            else:
                properties.append(indent + "  %s?: {\n" % (field_name,))

            properties += nested_properties
            properties.append(indent + "  }\n")

        # Generate nested list fields
        for field_name in serializer.many_nested_fields:
            field = all_fields[field_name]

            nested_properties = self._generate_fields(
                field.child,
                all_optional=all_optional,
                skip_readonly=skip_readonly,
                indent_level=indent_level + 1,
            )

            # Skip fields with no properties
            if len(nested_properties) < 1:
                continue

            if field_name in serializer.required_fields and not all_optional:
                properties.append(indent + "  %s: {\n" % (field_name,))
            else:
                properties.append(indent + "  %s?: {\n" % (field_name,))

            properties += nested_properties
            properties.append(indent + "  }[]\n")

        # Generate read only fields
        if not skip_readonly:
            for field_name in serializer.readonly_fields:
                if field_name not in serializer.simple_fields or (
                    skip_pk and field_name == getattr(serializer, "pk_field", None)
                ):
                    continue

                field = all_fields[field_name]

                if isinstance(field, serializers.ReadOnlyField):
                    # If the field is of type ReadOnly, then need to get the
                    # type directly from the model (if possible)

                    try:
                        model_field = getattr(
                            serializer.model_class, field.source or field_name
                        )
                        field_type_class = model_field.fget.__annotations__.get(
                            "return", "any"
                        )
                        field_type = PYTHON_TYPES.get(field_type_class, "any")
                        field_prop = gen_field(
                            field_name, field_type=field_type, readonly=True
                        )
                    except Exception as e:
                        field_type = "unknown"
                        field_prop = gen_field(
                            field_name, readonly=True
                        )
                        print(e)
                else:
                    field_prop = gen_field(field_name, readonly=True)

                properties.append(field_prop)

        return properties

    def generate_docs(self, filepath: str):
        """Convert serializers to typescript interfaces."""

        for serializer_class in self.serializer_classes:
            serializer = serializer_class()
            model_name = serializer.model_class.__name__
            model_article = self._get_model_article(model_name)

            idoc = INTERFACE_TPL % {
                "doc": serializer.__doc__,
                "model": model_name,
            }
            idoc_create = CREATE_INTERFACE_TPL % {
                "article": model_article,
                "model": model_name,
            }
            idoc_update = UPDATE_INTERFACE_TPL % {
                "article": model_article,
                "model": model_name,
            }

            all_fields = serializer.get_fields()

            # Set pk field as the first field
            idoc += self._generate_readonly_field(
                serializer.pk_field,
                self._get_field_type(all_fields[serializer.pk_field]),
                doc="Primary key",
            )

            main_fields = self._generate_fields(serializer)
            create_fields = self._generate_fields(
                serializer, skip_readonly=True, allow_null=True
            )
            update_fields = self._generate_fields(
                serializer,
                all_optional=True,
                skip_readonly=True,
                allow_null=True,
            )

            idoc += "".join(main_fields)
            idoc_create += "".join(create_fields)
            idoc_update += "".join(update_fields)

            idoc += "}\n"
            idoc_create += "}\n"
            idoc_update += "}\n"

            self.types_doc += idoc
            self.types_doc += "\n"
            self.types_doc += idoc_create
            self.types_doc += "\n"
            self.types_doc += idoc_update
            self.types_doc += "\n"
            self.types_doc += "\n"

        directory = "/".join(filepath.split("/")[:-1])
        os.makedirs(directory, exist_ok=True)

        with open(filepath, "w+") as f:
            f.write(self.types_doc)
