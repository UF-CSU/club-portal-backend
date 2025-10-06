"""
Abstract models for common fields.
"""

import uuid
from collections.abc import MutableMapping
from typing import Any, ClassVar, Optional, Self

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from utils.permissions import get_perm_label


class ManagerBase[T](models.Manager):
    """Extends django manager for improved db access."""

    model: type[T]

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
        """
        Use kwargs as lookup values, and update with defaults if exists
        or create with lookups and defaults otherwise.
        """
        return super().update_or_create(defaults, **kwargs)

    def all(self) -> models.QuerySet[T]:
        return super().all()


class ScopeType(models.TextChoices):
    """Permission levels."""

    GLOBAL = "global", _("Global")
    CLUB = "club", _("Club")


class ModelBase(models.Model):
    """
    Default fields for all models.

    Initializes created_at and updated_at fields,
    default __str__ method that returns name or display_name
    if the field exists on the model.
    """

    scope = ScopeType.GLOBAL  # TODO: Define scope has db column
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

    class Meta:
        abstract = True

    # Dynamic properties
    @property
    def admin_edit_url(self):
        """
        Get the url path for admin page to edit object.
        """
        app_label = self._meta.app_label
        model_name = self._meta.model_name
        admin_name = "admin"

        reverse_str = "%s:%s_%s_change" % (admin_name, app_label, model_name)

        return reverse_lazy(reverse_str, args=[self.pk])

    # Class methods
    @classmethod
    def get_content_type(cls):
        """
        Get ContentType object representing the model.

        This is a shorthand for: ``ContentType.objects.get_for_model(model)``
        """
        return ContentType.objects.get_for_model(cls)

    @classmethod
    def get_permissions(cls):
        """
        Get Permissions associated with this object. By default
        this will return: "add_model", "change_model", "delete_model", "view_model",
        with "model" being the name of the model.
        """

        return Permission.objects.filter(content_type=cls.get_content_type())

    @classmethod
    def get_permission_labels(cls):
        """
        Get list of labels representing the permissions that are available
        on this model. The standard format will usually return:
        "app.add_model", "app.change_model", "app.delete_model", "app.view_model"
        with "app" being the app name and "model" being the name of the model.
        """

        return [get_perm_label(perm) for perm in cls.get_permissions()]

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
    GITHUB = "github", _("GitHub")
    WEBSITE = "website", _("Personal Website")
    BLUESKY = "bluesky", _("BlueSky")
    SLACK = "slack", _("Slack")
    OTHER = "other", _("Other")


class SocialProfileBase(ModelBase):
    """Links to social media."""

    url = models.URLField(null=True, blank=True)
    username = models.CharField(null=True, blank=True)
    social_type = models.CharField(choices=SocialType.choices, blank=True)
    order = models.IntegerField(default=0, blank=True)

    class Meta:
        abstract = True
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.username or self.url} ({self.social_type})"

    def save(self, *args, **kwargs):
        if self.social_type or not self.url:
            return super().save(*args, **kwargs)

        if "discord" in self.url:
            self.social_type = SocialType.DISCORD
        elif "instagram" in self.url:
            self.social_type = SocialType.INSTAGRAM
        elif "facebook" in self.url:
            self.social_type = SocialType.FACEBOOK
        elif "twitter" in self.url or "x.com" in self.url:
            self.social_type = SocialType.TWITTER
        elif "linkedin" in self.url:
            self.social_type = SocialType.LINKEDIN
        elif "github" in self.url:
            self.social_type = SocialType.GITHUB
        elif "bsky" in self.url:
            self.social_type = SocialType.BLUESKY
        elif "slack" in self.url:
            self.social_type = SocialType.SLACK
        else:
            self.social_type = SocialType.OTHER

        return super().save(*args, **kwargs)


class MajorType(models.TextChoices):
    """Different types of academic majors."""

    CS = "cs", _("Computer Science")
    OTHER = "other", ("Other")
