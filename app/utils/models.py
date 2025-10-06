import os
import uuid
from pathlib import Path

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.core.files import File
from django.db import models
from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor
from django.utils.deconstruct import deconstructible
from rest_framework.fields import ObjectDoesNotExist

from utils.helpers import import_from_path
from utils.logging import print_error
from utils.types import T


@deconstructible
class UploadFilepathFactory:
    """
    Create function for model FileField to rename file and upload to a path.

    Parameters
    ----------
        path (str): Nested directory name in /media/uploads/ folder where the file will be uploaded.
            Ex: "/user/profile/" -> "/media/uploads/user/profile/"
    """

    def __init__(self, path: str, default_extension=None):
        self.path = path
        self.default_extension = default_extension

    def _parse_path(self, instance):
        try:
            path = self.path % {"id": instance.pk}
            return path
        except Exception:
            print_error()
            return self.path

    def __call__(self, instance, filename):
        if "." in filename:
            extension = filename.split(".")[-1]
        else:
            extension = self.default_extension or ""

        path = self._parse_path(instance)

        filename = f"{uuid.uuid4().hex}.{extension}"
        nested_dirs = [dirname for dirname in path.split("/") if dirname]
        return os.path.join("uploads", *nested_dirs, filename)


class UploadNestedClubFilepathFactory(UploadFilepathFactory):
    """Overrides the normal factory to render club id in the file path."""

    def _parse_path(self, instance):
        try:
            path = self.path % {"club_id": instance.club.pk}
            return path
        except Exception:
            print_error()
            return self.path


@deconstructible
class ValidateImportString:
    """
    Validate that a given string can be imported using the `import_from_path` function.
    """

    def __init__(self, target_type=None) -> None:
        self.target_type = target_type

    def __call__(self, text: str):
        symbol = import_from_path(text)
        assert issubclass(symbol, self.target_type), (
            f"Imported object needs to be of type {self.target_type}, but got {type(symbol)}."
        )


class ReverseOneToOneOrNoneDescriptor(ReverseOneToOneDescriptor):
    def __get__(self, instance, cls=None):
        try:
            return super().__get__(instance, cls)
        except ObjectDoesNotExist:
            return None


class OneToOneOrNoneField(models.OneToOneField[T]):
    """
    A OneToOneField that returns None if the related object doesn't exist.

    Source: <https://stackoverflow.com/questions/3955093/django-return-none-from-onetoonefield-if-related-object-doesnt-exist>
    """  # noqa: E501

    related_accessor_class = ReverseOneToOneOrNoneDescriptor


class ArrayChoiceField(ArrayField):
    """
    A field that allows us to store an array of choices.
    Uses Django's Postgres ArrayField
    and a MultipleChoiceField for its formfield.

    Source: <https://stackoverflow.com/a/39833588/10914922>
    """

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.MultipleChoiceField,
            "widget": forms.CheckboxSelectMultiple,
            "choices": self.base_field.choices,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)

    def clean(self, value, model_instance):
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str) and str(item).isnumeric():
                    value[i] = int(item)

        return super().clean(value, model_instance)


def save_file_to_model(model: models.Model, filepath, field="file"):
    """
    Given file path, save a file to a given model.

    This abstracts the process of opening the file and
    copying over the file data.
    """
    path = Path(filepath)

    with path.open(mode="rb") as f:
        file = File(f, name=path.name)
        setattr(model, field, file)
        model.save()
