"""
Abstract models for common fields.
"""

import uuid
from enum import Enum
from typing import Any, ClassVar, Generic, MutableMapping, Optional, Self

from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.types import T


class ManagerBase(models.Manager, Generic[T]):
    """Extends django manager for improved db access."""

    def create(self, **kwargs) -> T:
        """Create new model."""
        return super().create(**kwargs)

    def first(self) -> T | None:
        return super().first()

    def find_one(self, **kwargs) -> Optional[T]:
        """Return first model matching query, or none."""
        return self.filter_one(**kwargs)

    def find_by_id(self, id: int) -> Optional[T]:
        """Return model if exists, or none."""
        return self.find_one(id=id)

    def find(self, **kwargs) -> Optional[models.QuerySet[T]]:
        """Return models matching kwargs, or none."""
        query = self.filter(**kwargs)

        if not query.exists():
            return None

        return query

    def filter_one(self, **kwargs) -> Optional[T]:
        """Find object matching any of the fields (or)."""

        query = self.filter(**kwargs).order_by("-id")

        if not query.exists():
            return None
        else:
            return query.first()

    def get(self, *args, **kwargs) -> T:
        """Return object matching query, throw error if not found."""

        return super().get(*args, **kwargs)

    def get_by_id(self, id: int) -> T:
        """Return object with id, throw error if not found."""

        return self.get(id=id)

    def get_or_create(
        self, defaults: MutableMapping[str, Any] | None = None, **kwargs
    ) -> tuple[T, bool]:
        return super().get_or_create(defaults, **kwargs)

    def update_one(self, id: int, **kwargs) -> Optional[T]:
        """Update model if it exists."""

        self.filter(id=id).update(**kwargs)
        return self.find_by_id(id)

    def update_many(self, query: dict, **kwargs) -> models.QuerySet[T]:
        """
        Update models with kwargs if they match query.

        If the updated fields include the query fields, the default functionality
        would empty out the original query set - making the objects changed unknown.
        However, this function will rerun the filter with the updated fields, and
        return the result.
        """

        self.filter(**query).update(**kwargs)
        return self.filter(**kwargs)

    def delete_one(self, id: int) -> Optional[T]:
        """Delete model if exists."""
        obj = self.find_by_id(id)

        if obj:
            self.filter(id=id).delete()

        return obj

    def delete_many(self, **kwargs) -> list[T]:
        """Delete models that match query."""
        objs = self.filter(**kwargs)
        res = list(objs)

        objs.delete()

        return res

    def update_or_create(
        self, defaults: MutableMapping[str, Any] | None = None, **kwargs
    ) -> tuple[T, bool]:
        return super().update_or_create(defaults, **kwargs)

    def all(self) -> models.QuerySet[T]:
        return super().all()


class Scope(Enum):
    """Permission levels."""

    GLOBAL = "global"
    CLUB = "club"


class ModelBase(models.Model):
    """
    Default fields for all models.

    Initializes created_at and updated_at fields,
    default __str__ method that returns name or display_name
    if the field exists on the model.
    """

    scope = Scope.GLOBAL
    """Defines permissions level applied to model."""

    created_at = models.DateTimeField(auto_now_add=True, editable=False, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    objects: ClassVar[ManagerBase[Self]] = ManagerBase[Self]()

    def __str__(self) -> str:
        if hasattr(self, "name"):
            return self.name
        elif hasattr(self, "display_name"):
            return self.display_name

        return super().__str__()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def get_content_type(cls):
        """
        Get ContentType object representing the model.

        This is a shorthand for: ``ContentType.objects.get_for_model(model)``
        """
        return ContentType.objects.get_for_model(cls)

    @classmethod
    def get_fields_list(
        cls, include_parents=True, exclude_read_only=False
    ) -> list[str]:
        """Return a list of editable fields."""

        fields = [
            str(field.name)
            for field in cls._meta.get_fields(include_parents=include_parents)
            if (not exclude_read_only or (exclude_read_only and field.editable is True))
        ]

        return fields

    class Meta:
        abstract = True


class UniqueModel(ModelBase):
    """Default fields for globally unique database objects.

    id: Technical id and primary key, never revealed publicly outside of db.
        - If needed to change, it would need to be changed for every
          reference in database, which could cause linking issues

    uuid: Business id, can be shown to public or other services
        - If needed to change, regenerating would be easy and
          the only sideeffect is external services that use id. This could
          be solved by event-based communication between services.
    """

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True


class Color(models.TextChoices):
    """Default colors that tags can have."""

    RED = "red", _("Red")
    ORANGE = "orange", _("Orange")
    YELLOW = "yellow", _("Yellow")
    GREEN = "green", _("Green")
    BLUE = "blue", _("Blue")
    PURPLE = "purple", _("Purple")
    GREY = "grey", _("Grey")


class Tag(ModelBase):
    """Represents a category, tag, status, etc an object can have."""

    name = models.CharField(max_length=32, validators=[MinLengthValidator(2)])
    color = models.CharField(choices=Color.choices, default=Color.GREY)
    order = models.IntegerField(default=0, blank=True)

    class Meta:
        abstract = True
        ordering = ["order", "name"]


class SocialType(models.TextChoices):
    """Different types of accepted social accounts."""

    DISCORD = "discord", _("Discord")
    INSTAGRAM = "instagram", _("Instagram")
    FACEBOOK = "facebook", _("Facebook")
    TWITTER = "twitter", _("Twitter (X)")
    LINKEDIN = "linkedin", _("LinkedIn")


class SocialProfileBase(ModelBase):
    """Links to social media."""

    url = models.URLField(null=True, blank=True)
    username = models.CharField(null=True, blank=True)
    social_type = models.CharField(choices=SocialType.choices)
    order = models.IntegerField(default=0, blank=True)

    class Meta:
        abstract = True
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.username} ({self.social_type})"
