"""
Club models.
"""

# from datetime import datetime, timedelta

from typing import ClassVar, Optional, Union

from django.contrib.auth.models import Permission
from django.core import exceptions
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token

from core.abstracts.models import (
    ManagerBase,
    ModelBase,
    ScopeType,
    SocialProfileBase,
    Tag,
    UniqueModel,
)
from core.models import Major
from users.models import ApiKeyType, User, UserAgent
from utils.files import get_file_path
from utils.formatting import format_bytes
from utils.helpers import get_full_url, get_import_path
from utils.models import UploadNestedClubFilepathFactory
from utils.permissions import get_perm_label, get_permission, parse_permissions


class RoleType(models.TextChoices):
    """Different types of club roles."""

    ADMIN = "admin", _("Admin")
    VIEWER = "viewer", _("Viewer")
    CUSTOM = "custom", _("Custom")


class ClubTag(Tag):
    """Group clubs together based on topics."""


def get_default_founding_year():
    """Initializes default founding year to current year."""

    return timezone.now().year


def validate_max_founding_year(value: int):
    """Ensure founding year is not greater than current year."""
    current_year = timezone.now().year

    if value > current_year:
        raise ValueError(
            f"A club cannot have been founded in the future. Founding year must be greater than {current_year}."
        )


class ClubScopedModel:
    """Attributes required for an object scoped for clubs."""

    scope = ScopeType.CLUB

    # @property
    # def club(self) -> "Club":
    #     raise NotImplementedError(
    #         "Club scoped objects must have pointer to primary club."
    #     )

    @property
    def clubs(self) -> models.QuerySet["Club"]:
        """QuerySet of clubs allowed to access object."""

        if hasattr(self, "club"):
            return Club.objects.filter(id=self.club.id)

        raise NotImplementedError(
            "Club scoped objects must have pointer to all allowed clubs."
        )


class ClubManager(ManagerBase["Club"]):
    """Manage club queries."""

    def create(self, name: str, **kwargs):
        majors = kwargs.pop("majors", [])
        club = super().create(name=name, **kwargs)

        club.majors.set(majors)

        return club

    def filter_for_user(self, user: User):
        """Get clubs for user."""

        if user.is_superuser:
            return self.all()
        elif user.is_useragent and user.useragent.apikey_type == "club":
            # TODO: Abstract this useragent club
            return self.filter(id=user.useragent.club_apikey.club.id)

        return self.filter(memberships__user=user)

    def get_for_user(self, id: int, user: User):
        """Get club for user, or throw 404."""

        if user.is_superuser:
            return self.get(id=id)
        elif user.is_useragent and user.useragent.apikey_type == "club":
            # TODO: Abstract this useragent club
            key_club = user.useragent.club_apikey.club

            if key_club.id != id:
                raise self.model.DoesNotExist

            return key_club

        return self.get(id=id, memberships__user__id=user.id)


class Club(ClubScopedModel, UniqueModel):
    """Group of users."""

    name = models.CharField(max_length=64, unique=True)
    alias = models.CharField(max_length=7, unique=True, null=True, blank=True)
    logo: "ClubFile" = models.ForeignKey(
        "ClubFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    banner = models.ForeignKey(
        "ClubFile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    about = models.TextField(blank=True, null=True)
    founding_year = models.IntegerField(
        default=get_default_founding_year,
        validators=[MinValueValidator(1900), validate_max_founding_year],
    )

    contact_email = models.EmailField(null=True, blank=True)
    gatorconnect_url = models.URLField(
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                r"^https:\/\/orgs\.studentinvolvement\.ufl\.edu\/Organization\/"
            )
        ],
    )
    majors = models.ManyToManyField(
        Major, related_name="clubs", blank=True, help_text="Focused majors"
    )
    primary_color = models.CharField(
        blank=True, null=True, validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")]
    )
    text_color = models.CharField(
        blank=True, null=True, validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")]
    )

    # Relationships
    tags = models.ManyToManyField(ClubTag, blank=True)

    # Foreign Relationships
    memberships: models.QuerySet["ClubMembership"]
    teams: models.QuerySet["Team"]
    roles: models.QuerySet["ClubRole"]
    socials: models.QuerySet["ClubSocialProfile"]
    photos: models.QuerySet["ClubPhoto"]

    # Overrides
    objects: ClassVar[ClubManager] = ClubManager()

    @property
    def club(self):
        """Used for permissions checking."""
        return self

    @property
    def member_count(self) -> int:
        return self.memberships.count()

    class Meta:
        permissions = [("view_club_details", "Can view club details")]
        ordering = ["name", "-id"]

    def save(self, *args, **kwargs):
        # On save, set default alias from name
        try:
            if self.alias is None and len(self.name) >= 3:
                self.alias = self.name[0:3].upper()
            elif self.alias is None:
                self.alias = self.name.upper()
        except Exception:
            pass

        return super().save(*args, **kwargs)

    def clean(self):
        if self.alias is not None and not self.alias.isupper():
            self.alias = self.alias.upper()
        return super().clean()


class ClubFile(ClubScopedModel, ModelBase):
    """
    Represents a file that a club admin has uploaded to their media library.

    This allows club admins to upload banners, photo galleries,
    event documents, etc.
    """

    upload_file_path = UploadNestedClubFilepathFactory("clubs/%(club_id)s/files/")

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=upload_file_path)
    display_name = models.CharField(blank=True)

    # When uploading a new file, it must be required to set the uploaded_by field
    # for management purposes, but it should be ok to have null values in the database
    # for when a user is deleted, or if a file is generated, etc.
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        # Set display name to file name if not set
        if self.display_name is None or self.display_name == "":
            self.display_name = self.file.name
        return super().save(*args, **kwargs)

    @property
    def url(self) -> str:
        """Get the web url for the file."""
        return get_full_url(self.file.url)

    @property
    def size(self) -> str:
        """Get a string representation of the size of the file."""
        return format_bytes(self.file.size)

    @property
    def file_type(self) -> str:
        """Get the type of file stored (using file extension)."""
        try:
            return get_file_path(self.file).split(".")[-1]
        except Exception:
            return "Unknown"


class ClubPhoto(ClubScopedModel, ModelBase):
    """Photos for club carousel"""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="photos")
    file = models.ForeignKey(ClubFile, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "club"], name="unique_order_per_club"
            ),
        ]


class ClubSocialProfile(ClubScopedModel, SocialProfileBase):
    """Saves social media profile info for clubs."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="socials")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_social_urls_per_club",
                fields=["club", "social_type", "url"],
            )
        ]


class ClubRoleManager(ManagerBase["ClubRole"]):
    """Manage club role queries."""

    def create(
        self,
        club: Club,
        name: str,
        default=False,
        perm_labels=None,
        role_type=None,
        **kwargs,
    ):
        """
        Create new club role.

        Can either assign initial permissions by perm_labels as ``list[str]``, or
        by permissions as ``list[Permission]``.
        """
        from clubs.defaults import ADMIN_ROLE_PERMISSIONS, VIEWER_ROLE_PERMISSIONS

        # perm_labels = perm_labels if perm_labels is not None else []
        permissions = kwargs.pop("permissions", []) + parse_permissions(
            perm_labels or []
        )

        # Set default role type
        if role_type is None and len(permissions) > 0:
            role_type = RoleType.CUSTOM
        elif role_type is None:
            role_type = RoleType.VIEWER

        # Set default permissions if necessary
        if role_type == RoleType.ADMIN:
            permissions = parse_permissions(ADMIN_ROLE_PERMISSIONS)
        elif role_type == RoleType.VIEWER:
            perm_labels = parse_permissions(VIEWER_ROLE_PERMISSIONS)

        role = super().create(
            club=club, name=name, default=default, role_type=role_type, **kwargs
        )

        # for perm in perm_labels:
        #     perm = get_permission(perm)
        #     role.permissions.add(perm)

        # for perm in permissions:
        #     role.permissions.add(perm)
        role.permissions.set(permissions)
        role.save()

        return role


class ClubRole(ClubScopedModel, ModelBase):
    """Extend permission group to manage club roles."""

    name = models.CharField(max_length=32)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="roles")
    default = models.BooleanField(
        default=False,
        help_text="New members would be automatically assigned this role.",
    )
    permissions = models.ManyToManyField(Permission, blank=True)
    role_type = models.CharField(
        choices=RoleType.choices, default=RoleType.VIEWER, blank=True
    )

    # Meta fields
    cached_role_type = models.CharField(
        choices=RoleType.choices, default=None, blank=True, null=True, editable=False
    )

    # Dynamic Properties
    @property
    def perm_labels(self):
        """Sorted list of permissions labels."""
        labels = [get_perm_label(perm) for perm in self.permissions.all()]
        labels.sort()

        return labels

    # Overrides
    objects: ClassVar[ClubRoleManager] = ClubRoleManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("default", "club"),
                condition=models.Q(default=True),
                name="only_one_default_club_role_per_club",
            ),
            models.UniqueConstraint(
                fields=("name", "club"), name="unique_rolename_per_club"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.club})"

    def clean(self):
        """Validate and sync club roles on save."""
        if self.default:
            # Force all other roles to be false
            self.club.roles.exclude(id=self.id).update(default=False)

        return super().clean()

    def delete(self, *args, **kwargs):
        """Preconditions for club role deletion."""
        assert not self.default, "Cannot delete default club role."

        return super().delete(*args, **kwargs)


class ClubMembershipManager(ManagerBase["ClubMembership"]):
    """Manage queries for ClubMemberships."""

    def create(
        self,
        club: Club,
        user: User,
        roles: Optional[list[ClubRole | str]] = None,
        **kwargs,
    ):
        """Create new club membership."""
        roles = roles or []

        membership = super().create(club=club, user=user, **kwargs)

        if len(roles) < 1:
            default_role = club.roles.get(default=True)
            roles.append(default_role)

        for role in roles:
            if isinstance(role, str):
                role = ClubRole.objects.get(club=club, name=role)

            membership.roles.add(role)

        return membership

    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        roles = defaults.pop("roles", [])
        teams = defaults.pop("teams", [])

        membership, _ = super().update_or_create(defaults, **kwargs)
        membership.add_roles(*roles)

        for team in teams:
            TeamMembership.objects.get_or_create(team=team, user=membership.user)

        return membership


class ClubMembership(ClubScopedModel, ModelBase):
    """Connection between user and club."""

    club = models.ForeignKey(Club, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name="club_memberships", on_delete=models.CASCADE
    )

    is_owner = models.BooleanField(
        default=False,
        blank=True,
        help_text="Determines whether user is the sole superadmin for the club",
    )
    points = models.IntegerField(default=0, blank=True)
    roles = models.ManyToManyField(ClubRole, blank=True)

    # Meta fields
    cached_is_owner = models.BooleanField(
        default=False,
        blank=True,
        editable=False,
        help_text="Used to determine if is_owner has changed",
    )

    # Dynamic Properties
    @property
    def team_memberships(self):
        return self.user.team_memberships.filter(team__club__id=self.club.id)

    @property
    def is_admin(self) -> bool:
        """Indicates if user automatically gets all permissions for the club."""
        return self.is_owner or self.roles.filter(role_type=RoleType.ADMIN).exists()

    # Overrides
    objects: ClassVar[ClubMembershipManager] = ClubMembershipManager()

    def __str__(self):
        return self.user.__str__()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "club",
                    "is_owner",
                ),
                condition=models.Q(is_owner=True),
                name="only_one_owner_per_club",
            ),
            models.UniqueConstraint(
                name="one_membership_per_user_and_club", fields=("club", "user")
            ),
        ]

    # Methods
    def add_roles(self, *roles: ClubRole | str, commit=True):
        """Add ClubRole to membership."""

        for role in roles:
            if isinstance(role, str):
                role = ClubRole.objects.get(name=role, club=self.club)

            # If there's an issue, reverse all db ops
            with transaction.atomic():
                if role in self.roles.all():
                    continue

                self.roles.add(role)

                if commit:
                    self.save()

    def delete(self, *args, **kwargs):
        assert self.is_owner is False, "Cannot delete owner of club."

        return super().delete(*args, **kwargs)

    def clean(self):
        """Validate membership model."""

        # Handle changing of is_owner field
        if self.is_owner and not self.cached_is_owner:
            ClubMembership.objects.filter(club=self.club).update(is_owner=False)
            self.cached_is_owner = True
        elif not self.is_owner and self.cached_is_owner:
            self.cached_is_owner = False

        # Only proceed if already created
        if not self.pk:
            return super().clean()

        # Check that all roles are assigned to club
        for role in self.roles.all():
            if role.club.id != self.club.id:
                raise exceptions.ValidationError(
                    f"Club role {role} is not a part of club {self.club}."
                )

        return super().clean()


class TeamAccessType(models.TextChoices):
    """Define team access."""

    OPEN = "open"
    """Any one can join."""

    TEAM = "team"
    """Org and team admins can assign."""

    ORG = "org"
    """Only org admins can assign."""

    CLOSED = "closed"
    """No one can join."""


class Team(ClubScopedModel, ModelBase):
    """Smaller groups within clubs."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="teams")

    name = models.CharField(max_length=64)
    points = models.IntegerField(default=0, blank=True)

    access = models.CharField(
        choices=TeamAccessType.choices, default=TeamAccessType.OPEN
    )

    # Foreign Relationships
    memberships: models.QuerySet["TeamMembership"]
    roles: models.QuerySet["TeamRole"]

    # Overrides
    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_team_per_club", fields=("club", "name")
            )
        ]


class TeamRoleManager(ManagerBase["TeamRole"]):
    """Manage queries for team roles."""

    def create(self, team: Team, name: str, default=False, perm_labels=None, **kwargs):
        """
        Create new team role.

        Can either assign initial permissions by perm_labels as ``list[str]``, or
        by permissions as ``list[Permission]``.
        """
        perm_labels = perm_labels if perm_labels is not None else []
        permissions = kwargs.pop("permissions", [])

        role = super().create(team=team, name=name, default=default, **kwargs)

        for perm in perm_labels:
            perm = get_permission(perm)
            role.permissions.add(perm)

        for perm in permissions:
            role.permissions.add(perm)

        return role


class TeamRole(ClubScopedModel, ModelBase):
    """Extend permission group to manage club roles."""

    name = models.CharField(max_length=32)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="roles")
    default = models.BooleanField(
        default=False,
        help_text="New members would be automatically assigned this role.",
    )
    permissions = models.ManyToManyField(Permission, blank=True)
    order = models.PositiveIntegerField(
        default=0, help_text="Used to determine the list ordering of a team member"
    )
    role_type = models.CharField(
        choices=RoleType.choices, default=RoleType.VIEWER, blank=True
    )

    # TODO: Implement cached_role_type, signals

    # Dynamic properties
    @property
    def club(self):
        return self.team.club

    # Overrides
    objects: ClassVar[TeamRoleManager] = TeamRoleManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("default", "team"),
                condition=models.Q(default=True),
                name="only_one_default_team_role_per_team",
            ),
            models.UniqueConstraint(
                fields=("name", "team"), name="unique_rolename_per_team"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.team})"

    def clean(self):
        """Validate and sync team roles on save."""
        if self.default:
            # Force all other roles to be false
            self.team.roles.exclude(id=self.id).update(default=False)

        return super().clean()

    def delete(self, *args, **kwargs):
        """Preconditions for team role deletion."""
        assert not self.default, "Cannot delete default team role."

        return super().delete(*args, **kwargs)


class TeamMembershipManager(ManagerBase["TeamMembership"]):
    """Manage queries for TeamMemberships."""

    def create(
        self, team: Team, user: User, roles: Optional[list[ClubRole]] = None, **kwargs
    ):
        """Create new team membership."""
        roles = roles if roles is not None else []

        if not user.club_memberships.filter(club__id=team.club.id).exists():
            ClubMembership.objects.create(team.club, user)

        membership = super().create(team=team, user=user, **kwargs)

        if len(roles) < 1:
            try:
                default_role = team.roles.get(default=True)
                roles.append(default_role)
            except Exception:
                pass

        for role in roles:
            membership.roles.add(role)

        return membership

    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        roles = defaults.pop("roles", [])

        membership = self.filter_one(**defaults)
        if not membership:
            membership = self.create(roles=roles, **{**defaults, **kwargs})
        else:
            self.filter(id=membership.id).update(**kwargs)
            membership.refresh_from_db()

            if len(roles) > 0:
                membership.roles.set(roles, clear=True)

        return membership


class TeamMembership(ClubScopedModel, ModelBase):
    """Manage club member's assignment to a team."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="team_memberships"
    )
    roles = models.ManyToManyField(TeamRole, blank=True)
    order_override = models.PositiveIntegerField(null=True, blank=True)

    # Custom properties
    @property
    def order(self) -> int:
        if self.order_override:
            return self.order_override

        roles = self.roles.order_by("order")
        if not roles.exists():
            return 0

        return roles.first().order

    @property
    def club(self):
        return self.team.club

    @order.setter
    def order(self, value: int):
        self.order_override = value

    # Overrides
    objects: ClassVar["TeamMembershipManager"] = TeamMembershipManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="user_single_team_membership", fields=("user", "team")
            )
        ]

    def clean(self):
        """Run model validation."""

        if not self.user.club_memberships.filter(club__id=self.team.club.id).exists():
            raise exceptions.ValidationError(
                f"User must be a member of club {self.team.club} to join team {self.team}."
            )

        return super().clean()

    def add_roles(self, *roles, commit=True):
        """Add TeamRole to membership."""

        for role in roles:
            # If there's an issue, reverse all db ops
            with transaction.atomic():
                if role in self.roles.all():
                    continue

                self.roles.add(role)

                if commit:
                    self.save()


class ClubApiKeyManager(ManagerBase["ClubApiKey"]):
    """Manage queries and operations for club api tokens."""

    def create(
        self,
        club: Club,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list[Union[str, int, "Permission"]]] = None,
        **kwargs,
    ):
        """
        Create new api key for a club.

        Can either assign initial permissions by perm_labels as ``list[str]``, or
        by permissions as ``list[Permission]``.
        """
        perm_objs = parse_permissions(permissions, fail_silently=False)

        key = super().create(
            club=club,
            name=name,
            description=description,
            **kwargs,
        )

        for perm in perm_objs:
            key.permissions.add(perm)

        return key


class ClubApiKey(ClubScopedModel, ModelBase):
    """
    Allow external systems to make authorized api requests.

    Named "ApiKey" to not conflict with "Token" verbage used by DRF.
    """

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    user_agent = models.OneToOneField(
        UserAgent, on_delete=models.PROTECT, related_name="club_apikey", blank=True
    )

    name = models.CharField(max_length=32)
    description = models.TextField(null=True, blank=True)

    permissions = models.ManyToManyField(
        Permission, blank=True, help_text="Allowed permissions for this club only."
    )

    objects: ClassVar[ClubApiKeyManager] = ClubApiKeyManager()

    @property
    def secret(self) -> str:
        """Property accessor for the secret."""

        return self.get_secret()

    # Overrides
    class Meta:
        verbose_name = "Api Key"
        constraints = [
            models.UniqueConstraint(
                name="unique_apikey_name_per_club", fields=("name", "club")
            )
        ]

    def save(self, *args, **kwargs):
        if self.user_agent_id is None:
            username = f"agent-c{self.club.id}-" + slugify(self.name)
            self.user_agent = UserAgent.objects.create(
                username=username, apikey_type=ApiKeyType.CLUB
            )
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=None):
        """Delete self and clean up related models."""

        user_agent = self.user_agent
        res = super().delete(using, keep_parents)

        Token.objects.filter(user=user_agent).delete()
        user_agent.delete()

        new_res = (
            res[0] + 2,
            {**res[1], get_import_path(Token): 1, get_import_path(UserAgent): 1},
        )

        return new_res

    # Methods
    def get_token(self):
        """Get API token to use in requests."""

        token, _ = Token.objects.get_or_create(user=self.user_agent)
        return token

    def get_secret(self):
        """Get secret string."""

        return self.get_token().key
