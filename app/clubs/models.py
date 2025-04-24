"""
Club models.
"""

# from datetime import datetime, timedelta
from typing import ClassVar, Optional, Union

from django.contrib.auth.models import Permission
from django.core import exceptions
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.authtoken.models import Token

from core.abstracts.models import (
    ManagerBase,
    ModelBase,
    Scope,
    SocialProfileBase,
    Tag,
    UniqueModel,
)
from users.models import KeyType, User, UserAgent
from utils.helpers import get_import_path
from utils.models import UploadFilepathFactory
from utils.permissions import get_permission, parse_permissions


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


class Club(UniqueModel):
    """Group of users."""

    scope = Scope.CLUB
    get_logo_filepath = UploadFilepathFactory("clubs/logos/")

    name = models.CharField(max_length=64, unique=True)
    logo = models.ImageField(upload_to=get_logo_filepath, blank=True, null=True)

    alias = models.CharField(max_length=7, unique=True, null=True, blank=True)
    about = models.TextField(blank=True, null=True)
    founding_year = models.IntegerField(
        default=get_default_founding_year,
        validators=[MinValueValidator(1900), validate_max_founding_year],
    )
    contact_email = models.EmailField(null=True, blank=True)

    tags = models.ManyToManyField(ClubTag, blank=True)

    # Relationships
    memberships: models.QuerySet["ClubMembership"]
    teams: models.QuerySet["Team"]
    roles: models.QuerySet["ClubRole"]
    socials: models.QuerySet["ClubSocialProfile"]

    # Overrides
    @property
    def club(self):
        """Used for permissions checking."""
        return self

    class Meta:
        permissions = [("preview_club", "Can view a set of limited fields for a club.")]
        ordering = ["name", "-id"]

    def save(self, *args, **kwargs):
        # On save, set default alias from name
        try:
            if self.alias is None and len(self.name) >= 3:
                self.alias = self.name[0:3].capitalize()
            elif self.alias is None:
                self.alias = self.name.capitalize()
        except Exception:
            pass

        return super().save(*args, **kwargs)


class ClubSocialProfile(SocialProfileBase):
    """Saves social media profile info for clubs."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="socials")


class ClubRoleManager(ManagerBase["ClubRole"]):
    """Manage club role queries."""

    def create(self, club: Club, name: str, default=False, perm_labels=None, **kwargs):
        """
        Create new club role.

        Can either assign initial permissions by perm_labels as ``list[str]``, or
        by permissions as ``list[Permission]``.
        """
        perm_labels = perm_labels if perm_labels is not None else []
        permissions = kwargs.pop("permissions", [])

        role = super().create(club=club, name=name, default=default, **kwargs)

        for perm in perm_labels:
            perm = get_permission(perm)
            role.permissions.add(perm)

        for perm in permissions:
            role.permissions.add(perm)

        return role


class ClubRole(ModelBase):
    """Extend permission group to manage club roles."""

    name = models.CharField(max_length=32)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="roles")
    default = models.BooleanField(
        default=False,
        help_text="New members would be automatically assigned this role.",
    )
    permissions = models.ManyToManyField(Permission, blank=True)

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
        self, club: Club, user: User, roles: Optional[list[ClubRole]] = None, **kwargs
    ):
        """Create new club membership."""
        roles = roles if roles is not None else []

        membership = super().create(club=club, user=user, **kwargs)

        if len(roles) < 1:
            default_role = club.roles.get(default=True)
            roles.append(default_role)

        for role in roles:
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


class ClubMembership(ModelBase):
    """Connection between user and club."""

    club = models.ForeignKey(Club, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name="club_memberships", on_delete=models.CASCADE
    )

    is_owner = models.BooleanField(default=False, blank=True)
    points = models.IntegerField(default=0, blank=True)
    roles = models.ManyToManyField(ClubRole, blank=True)

    # Foreign Relationships
    # teams: models.QuerySet["Team"]

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

    def add_roles(self, *roles, commit=True):
        """Add ClubRole to membership."""

        for role in roles:
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
        if not self.pk:
            return super().clean()

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


class Team(ModelBase):
    """Smaller groups within clubs."""

    scope = Scope.CLUB
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


class TeamRole(ModelBase):
    """Extend permission group to manage club roles."""

    name = models.CharField(max_length=32)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="roles")
    default = models.BooleanField(
        default=False,
        help_text="New members would be automatically assigned this role.",
    )
    permissions = models.ManyToManyField(Permission, blank=True)

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


class TeamMembership(ModelBase):
    """Manage club member's assignment to a team."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="team_memberships"
    )
    roles = models.ManyToManyField(TeamRole, blank=True)

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
        username = f"agent-c{club.id}-" + slugify(name)
        user_agent = UserAgent.objects.create(
            username=username, apikey_type=KeyType.CLUB
        )

        perm_objs = parse_permissions(permissions, fail_silently=False)

        key = super().create(
            club=club,
            user_agent=user_agent,
            name=name,
            description=description,
            **kwargs,
        )

        for perm in perm_objs:
            key.permissions.add(perm)

        return key


class ClubApiKey(ModelBase):
    """
    Allow external systems to make authorized api requests.

    Named "ApiKey" to not conflict with "Token" verbage used by DRF.
    """

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    user_agent = models.OneToOneField(
        UserAgent, on_delete=models.PROTECT, related_name="club_apikey"
    )

    name = models.CharField(max_length=32)
    description = models.TextField(null=True, blank=True)

    permissions = models.ManyToManyField(
        Permission, blank=True, help_text="Allowed permissions for this club only."
    )

    objects: ClassVar[ClubApiKeyManager] = ClubApiKeyManager()

    @property
    def secret(self):
        """Property accessor for the secret."""

        return self.get_secret()

    # Overrides
    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_apikey_name_per_club", fields=("name", "club")
            )
        ]

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
