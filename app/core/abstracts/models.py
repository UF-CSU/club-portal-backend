"""
Abstract models for common fields.
"""

import uuid
from collections.abc import MutableMapping
from typing import Any, ClassVar, Optional, Self

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.core.validators import MinLengthValidator
from django.db import models, transaction
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from utils.permissions import get_perm_label, parse_permissions


class CustomManagerMethods[T]:
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


class QuerySetBase[T](CustomManagerMethods[T], models.QuerySet):
    """Extends default queryset to provide extra methods."""

    pass


class ManagerBase[T](
    CustomManagerMethods[T], models.Manager.from_queryset(QuerySetBase[T])
):
    """Extends django manager for improved db access."""

    pass


# ManagerBase = _ManagerBase[M].from_queryset(QuerySetBase)


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

    objects: ClassVar[QuerySetBase[Self]] = QuerySetBase.as_manager()

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


class RoleType(models.TextChoices):
    """Different types of club roles."""

    ADMIN = "admin", _("Admin")
    EDITOR = "editor", _("Editor")
    VIEWER = "viewer", _("Viewer")
    FOLLOWER = "follower", _("Follower")
    CUSTOM = "custom", _("Custom")


class RoleManagerBase(ManagerBase["RoleBase"]):
    """Manage role queries."""

    def create(
        self,
        *,
        name: str,
        is_default=False,
        perm_labels=None,
        role_type: RoleType | None = None,
        **kwargs,
    ):
        """
        Create new role.

        Can either assign initial permissions by perm_labels as ``list[str]``, or
        by permissions as ``list[Permission]``.
        """
        permissions = kwargs.pop("permissions", []) + parse_permissions(
            perm_labels or []
        )

        # Set role type
        if role_type is None:
            if len(permissions) > 0:
                role_type = RoleType.CUSTOM
            else:
                role_type = RoleType.VIEWER
        assert role_type is not None

        # Set permissions
        if role_type != RoleType.CUSTOM:
            perms_mapping = self.model.get_permissions_by_role_type()
            permissions = parse_permissions(perms_mapping[role_type])

        role = super().create(
            name=name, is_default=is_default, role_type=role_type, **kwargs
        )

        role.permissions.set(permissions)
        role.save()

        return role


class RoleBase(ModelBase):
    """Extend permission group to manage roles."""

    name = models.CharField(max_length=32)

    role_type = models.CharField(
        choices=RoleType.choices, default=RoleType.VIEWER, blank=True
    )
    order = models.PositiveIntegerField(
        default=0, help_text="Used to determine the list ordering of a member"
    )
    permissions = models.ManyToManyField(Permission, blank=True)

    # Flags
    is_default = models.BooleanField(
        default=False,
        help_text="New members would be automatically assigned this role.",
    )

    # Meta fields
    cached_role_type = models.CharField(
        choices=RoleType.choices, default=None, blank=True, null=True, editable=False
    )

    # Dynamic Properties
    @cached_property
    def perm_labels(self):
        """Sorted list of permissions labels."""
        labels = [get_perm_label(perm) for perm in self.permissions.all()]
        labels.sort()

        return labels

    # Overrides
    objects: ClassVar[RoleManagerBase] = RoleManagerBase()

    class Meta:
        ordering = [
            "order"
        ]
        abstract = True

    def __str__(self):
        return f"{self.name} ({self.group()})"

    def clean(self):
        """Validate and sync roles on save."""
        if self.is_default:
            # Force all other roles to be false
            self.group().roles.exclude(id=self.id).update(is_default=False)

        return super().clean()

    def delete(self, *args, **kwargs):
        """Preconditions for role deletion."""
        assert not self.is_default, "Cannot delete default role."

        return super().delete(*args, **kwargs)

    # Abstract methods
    def group(self) -> ModelBase:
        raise NotImplementedError(
            "Role objects must return group that contains the roles"
        )

    @classmethod
    def get_permissions_by_role_type(self) -> dict[RoleType, list[str]]:
        raise NotImplementedError(
            "Role objects must return mapping between role type presets and permissions"
        )

    # Attach signal
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Lazy to avoid circular import
        from core.abstracts.signals import on_save_role

        models.signals.post_save.connect(on_save_role, sender=cls)


class MembershipManagerBase(ManagerBase["MembershipBase"]):
    """Manage queries for Memberships."""
    def create(
        self,
        *,
        user,
        roles: Optional[list[RoleBase | str]] = None,
        **kwargs,
    ):
        """Create new membership."""
        roles = roles or []

        membership = super().create(user=user, **kwargs)

        if len(roles) < 1:
            try:
                default_role = membership.group().roles.get(is_default=True)
                roles.append(default_role)
            except Exception:
                # Club has no default role
                pass

        for role in roles:
            if isinstance(role, str):
                role = membership.group().roles.get(name=role)

            membership.roles.add(role)

        return membership

    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        roles = defaults.pop("roles", [])

        membership = self.filter_one(**defaults)
        created = False
        if not membership:
            membership = self.create(roles=roles, **{**defaults, **kwargs})
            created = True
        else:
            self.filter(id=membership.id).update(**kwargs)
            membership.refresh_from_db()

            if len(roles) > 0:
                membership.roles.set(roles, clear=True)

        return membership, created

    def _filter_is_role(self, role_type: RoleType):
        """Filter memberships that are this role."""
        queryset = self.prefetch_related("roles")
        filtered = [m.id for m in queryset if m._is_role(role_type)]
        return self.filter(id__in=filtered)

    def _filter_is_not_role(self, role_type: RoleType):
        """Filter memberships that are not this role."""
        queryset = self.prefetch_related("roles")
        filtered = [m.id for m in queryset if not m._is_role(role_type)]
        return self.filter(id__in=filtered)

    def filter_is_admin(self):
        """Filter memberships that are admin memberships."""

        return self._filter_is_role(RoleType.ADMIN)

    def filter_is_not_admin(self):
        """Filter memberships that are not admin memberships."""

        return self._filter_is_not_role(RoleType.ADMIN)


class MembershipBase(ModelBase):
    """Manage member's assignment to a group."""

    # Properties overridden in subclass
    user = None # models.ForeignKey(User, on_delete=models.CASCADE)
    roles = None # models.ManyToManyField(RoleBase, blank=True)

    # Meta fields
    order_override = models.PositiveIntegerField(null=True, blank=True)

    # Dynamic Properties
    @property
    def order(self) -> int:
        if self.order_override:
            return self.order_override

        roles = self.roles.all()

        if len(roles) == 0:
            return 0
        return roles[0].order

    @order.setter
    def order(self, value: int):
        self.order_override = value

    @property
    def _has_all_permissions(self) -> bool:
        # Superusers have all permissions
        return self.user.is_superuser

    @property
    def _permissions(self) -> list[str]:
        """All the permissions of a member."""
        if self._has_all_permissions:
            perms_mapping = self.role_model().get_permissions_by_role_type()
            return perms_mapping[RoleType.ADMIN]

        permissions = set()
        for r in self.roles.all():
            permissions.update(r.perm_labels)
        return list(permissions)

    def _is_role(self, role_type: RoleType) -> bool:
        """Helper method to determine if a member is a role"""
        permissions = set(self._permissions)

        perms_mapping = self.role_model().get_permissions_by_role_type()
        role_permissions = set(perms_mapping[role_type])

        return role_permissions.issubset(permissions)

    @property
    def is_admin(self) -> bool:
        """Indicates if member is an admin for a group."""
        return self._is_role(RoleType.ADMIN)

    @property
    def is_editor(self) -> bool:
        """Indicates if member is an editor for a group."""
        return self._is_role(RoleType.EDITOR)

    @property
    def is_viewer(self) -> bool:
        """Indicates if member is a viewer for a group."""
        return self._is_role(RoleType.VIEWER)

    @property
    def is_follower(self) -> bool:
        """Indicates if member is a follower for a group."""
        return self._is_role(RoleType.FOLLOWER)

    def _is_flag(self, flag: str) -> bool:
        """Helper method to determine if a member has a role with a flag"""

        return any(getattr(r, flag, False) for r in self.roles.all())

    # Overrides
    objects: ClassVar[MembershipManagerBase] = MembershipManagerBase()

    def __str__(self):
        return self.user.__str__()

    class Meta:
        abstract = True

    def add_roles(self, *roles: RoleBase | str, commit=True):
        """Add role to membership."""

        for role in roles:
            if isinstance(role, str):
                role = self.group().roles.get(name=role)

            # If there's an issue, reverse all db ops
            with transaction.atomic():
                if role in self.roles.all():
                    continue

                self.roles.add(role)

                if commit:
                    self.save()

    def clean(self):
        """Validate membership model."""

        # Only proceed if already created
        if not self.pk:
            return super().clean()

        # Check that all roles are assigned to club
        for role in self.roles.all():
            if role.group().id != self.group().id:
                raise exceptions.ValidationError(
                    f"Role {role} is not a part of group {self.group()}."
                )

        return super().clean()

    # Abstract methods
    def group(self) -> ModelBase:
        raise NotImplementedError(
            "Membership objects must return group that contains the memberships"
        )

    @classmethod
    def role_model(self) -> type[RoleBase]:
        raise NotImplementedError(
            "Membership objects must return role model"
        )