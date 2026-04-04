"""
Club models.
"""

# from datetime import datetime, timedelta

from typing import ClassVar, Optional, Union

from clubs.defaults import (
    ADMIN_ROLE_PERMISSIONS,
    EDITOR_ROLE_PERMISSIONS,
    FOLLOWER_ROLE_PERMISSIONS,
    VIEWER_ROLE_PERMISSIONS,
)
from core.abstracts.models import (
    ManagerBase,
    MembershipBase,
    MembershipBaseManager,
    ModelBase,
    RoleBase,
    RoleType,
    ScopeType,
    SocialProfileBase,
    Tag,
    UniqueModel,
)
from core.models import Major
from django.contrib.auth.models import Permission
from django.core import exceptions
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token
from users.models import ApiKeyType, User, UserAgent
from utils.formatting import format_bytes
from utils.helpers import get_full_url, get_import_path
from utils.models import UploadNestedClubFilepathFactory
from utils.permissions import parse_permissions


class ClubFileOrigin(models.TextChoices):
    """Defines different places a file could have come from."""

    ADMIN = "admin", "Admin Dashboard"
    SUBMISSION = "submission", "Poll Submission"


class ClubTag(Tag):
    """Group clubs together based on topics."""

    clubs: models.QuerySet["Club"]


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
        elif user.is_anonymous:
            return self.none()
        elif (
            getattr(user, "is_useragent", False)
            and user.useragent.apikey_type == "club"
        ):
            # TODO: Abstract this useragent club
            return self.filter(id=user.useragent.club_apikey.club.id)

        return self.filter(memberships__user=user)

    def get_for_user(self, id: int, user: User):
        """Get club for user, or throw 404."""

        if user.is_superuser:
            return self.get(id=id)
        elif (
            getattr(user, "is_useragent", False)
            and user.useragent.apikey_type == "club"
        ):
            # TODO: Abstract this useragent club
            key_club = user.useragent.club_apikey.club

            if key_club.id != id:
                raise self.model.DoesNotExist

            return key_club

        return self.get(id=id, memberships__user__id=user.id)


class Club(ClubScopedModel, UniqueModel):
    """Group of users."""

    name = models.CharField(max_length=100, unique=True)
    alias = models.CharField(max_length=15, null=True, blank=True)

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

    instagram_followers = models.IntegerField(null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    primary_color = models.CharField(
        blank=True, null=True, validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")]
    )
    text_color = models.CharField(
        blank=True, null=True, validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")]
    )

    is_csu_partner = models.BooleanField(
        default=False, help_text="Is this club shown on the csu site?"
    )
    mirror_gatorconnect = models.BooleanField(
        default=True,
        help_text="Should this club be updated based on info from gatorconnect?",
    )
    # allow_beta_access = models.BooleanField(
    #     default=False, help_text="Allow access to beta features."
    # )
    # allow_alpha_access = models.BooleanField(
    #     default=False, help_text="Allow access to alpha features."
    # )

    # GatorConnect fields
    gatorconnect_url = models.URLField(
        null=True,
        blank=True,
        help_text="Link to the gatorconnect page",
        validators=[
            RegexValidator(
                r"^https:\/\/orgs\.studentinvolvement\.ufl\.edu\/Organization\/"
            )
        ],
    )
    gatorconnect_organization_id = models.IntegerField(null=True, blank=True)
    gatorconnect_organization_guid = models.TextField(null=True, blank=True)
    gatorconnect_organization_url = models.TextField(
        null=True, blank=True, help_text="How they assign links to clubs"
    )

    # Relationships
    tags = models.ManyToManyField(ClubTag, blank=True, related_name="clubs")
    majors = models.ManyToManyField(
        Major, related_name="clubs", blank=True, help_text="Focused majors"
    )

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

    @cached_property
    def member_count(self) -> int:
        return getattr(self, "_member_count", None) or self.memberships.count()

    @cached_property
    def owner(self):
        if hasattr(self, "prefetched_owner_memberships"):
            return (
                self.prefetched_owner_memberships[0].user
                if self.prefetched_owner_memberships
                else None
            )
        try:
            return self.memberships.get(is_owner=True).user
        except ClubMembership.DoesNotExist:
            return None

    @property
    def is_claimed(self) -> bool:
        """Club has an owner and that owner can authenticate."""
        if self.owner:
            return self.owner.can_authenticate
        else:
            return False

    @property
    def default_role(self) -> str:
        return self.roles.get(is_default=True).name

    @property
    def executives(self):
        return self.memberships.filter(roles__is_executive=True)

    @property
    def roster_teams(self):
        return self.teams.filter(show_on_roster=True)

    class Meta:
        permissions = [
            ("view_club_details", "Can view club details"),
            ("can_vote", "Can vote"),
        ]
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
    origin = models.CharField(
        choices=ClubFileOrigin.choices, default=ClubFileOrigin.ADMIN, blank=True
    )

    # Dynamic properties
    @property
    def submission(self):
        return getattr(self, "_submission", None)

    @property
    def url(self) -> str:
        """Get the web url for the file."""
        return get_full_url(self.file.url)

    @cached_property
    def size(self) -> str:
        """Get a string representation of the size of the file."""
        return format_bytes(self.file.size)

    @cached_property
    def file_type(self) -> str:
        """Get the type of file stored (using file extension)."""
        try:
            return self.file.name.split(".")[-1]
        except Exception:
            return "Unknown"

    # Overrides
    def save(self, *args, **kwargs):
        # Set display name to file name if not set
        if self.display_name is None or self.display_name == "":
            self.display_name = self.file.name
        return super().save(*args, **kwargs)


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


class ClubRole(ClubScopedModel, RoleBase):
    """Extend permission group to manage club roles."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="roles")

    # Flags
    is_official = models.BooleanField(
        default=True,
        help_text="Users with this role are counted towards official membership tallies.",
    )
    is_voter = models.BooleanField(
        default=False,
        help_text="Users with this role will be marked as able to vote.",
    )
    is_executive = models.BooleanField(
        default=False,
        help_text="Users with this role will be returned when a club's executives are queried.",
    )

    class Meta(RoleBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("is_default", "club"),
                condition=models.Q(is_default=True),
                name="only_one_default_club_role_per_club",
            ),
            models.UniqueConstraint(
                fields=("name", "club"), name="unique_rolename_per_club"
            ),
        ]

    # Abstract methods
    def group(self) -> Club:
        return self.club

    @classmethod
    def get_permissions_by_role_type(self) -> dict[RoleType, list[str]]:
        return {
            RoleType.FOLLOWER: FOLLOWER_ROLE_PERMISSIONS,
            RoleType.VIEWER: VIEWER_ROLE_PERMISSIONS,
            RoleType.EDITOR: EDITOR_ROLE_PERMISSIONS,
            RoleType.ADMIN: ADMIN_ROLE_PERMISSIONS
        }

class ClubMembershipManager(MembershipBaseManager):
    """Manage queries for ClubMemberships."""

    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        teams = defaults.pop("teams", [])

        membership, created = super().update_or_create(defaults, **kwargs)

        for team in teams:
            TeamMembership.objects.get_or_create(team=team, user=membership.user)

        return membership, created


class ClubMembership(ClubScopedModel, MembershipBase):
    """Connection between user and club."""

    club = models.ForeignKey(Club, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name="club_memberships", on_delete=models.CASCADE
    )
    points = models.IntegerField(default=0, blank=True)
    roles = models.ManyToManyField(ClubRole, blank=True)

    # Flags
    is_owner = models.BooleanField(
        default=False,
        blank=True,
        help_text="Determines whether user is the sole superadmin for the club.",
    )
    is_pinned = models.BooleanField(
        default=False, blank=True, help_text="Club is pinned on user's dashboard."
    )
    enable_notifications = models.BooleanField(
        default=True, help_text="The user get notifications for this club."
    )

    # Meta fields
    cached_is_owner = models.BooleanField(
        default=False,
        blank=True,
        editable=False,
        help_text="Used to determine if is_owner has changed",
    )

    # Dynamic Properties
    @cached_property
    def team_memberships(self):
        return self.user.team_memberships.filter(team__club_id=self.club_id)

    @property
    def _has_all_permissions(self) -> bool:
        if self.is_owner:
            return True
        return super()._has_all_permissions

    @property
    def is_voter(self) -> bool:
        """Indicates if a user has a voter role."""
        return self._is_flag("is_voter")

    # Overrides
    objects: ClassVar[ClubMembershipManager] = ClubMembershipManager()

    class Meta:
        permissions = [("view_executive_clubmembership", "View executive members")]
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

        return super().clean()

    # Abstract methods
    def group(self) -> ModelBase:
        return self.club

    @classmethod
    def role_model(self) -> type[RoleBase]:
        return ClubRole


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

    show_on_roster = models.BooleanField(
        default=False, help_text="Show this team on the club's roster."
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


class TeamRole(ClubScopedModel, RoleBase):
    """Extend permission group to manage club roles."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="roles")

    # Dynamic properties
    @property
    def club(self):
        return self.team.club

    class Meta(RoleBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("is_default", "team"),
                condition=models.Q(is_default=True),
                name="only_one_default_team_role_per_team",
            ),
            models.UniqueConstraint(
                fields=("name", "team"), name="unique_rolename_per_team"
            ),
        ]

    # Abstract methods
    def group(self) -> Team:
        return self.team

    @classmethod
    def get_permissions_by_role_type(self) -> dict[RoleType, list[str]]:
        # TODO: Create permissions for TeamRole
        return {
            RoleType.FOLLOWER: [],
            RoleType.VIEWER: [],
            RoleType.EDITOR: [],
            RoleType.ADMIN: []
        }


class TeamMembershipManager(MembershipBaseManager):
    """Manage queries for TeamMemberships."""

    def create(
        self, team: Team, user: User, roles: Optional[list[ClubRole]] = None, **kwargs
    ):
        """Create new team membership."""
        if not user.club_memberships.filter(club__id=team.club.id).exists():
            ClubMembership.objects.create(club=team.club, user=user)

        roles = roles or []

        membership = super().create(team=team, user=user, roles=roles, **kwargs)

        return membership

class TeamMembership(ClubScopedModel, MembershipBase):
    """Manage club member's assignment to a team."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="team_memberships"
    )
    roles = models.ManyToManyField(TeamRole, blank=True)

    # Custom properties
    @property
    def club(self):
        return self.team.club

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

    # Abstract methods
    def group(self) -> ModelBase:
        return self.team

    @classmethod
    def role_model(self) -> type[RoleBase]:
        return TeamRole


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

    def get_secret(self):
        """Get secret string."""

        return self.get_token().key
