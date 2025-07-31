"""
User Models.
"""

import random
import string
from typing import ClassVar, Optional

from django.contrib import auth
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import PermissionDenied
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import MaxValueValidator

from core.abstracts.models import ManagerBase, ModelBase, SocialProfileBase, UniqueModel
from lib.countries import CountryField
from utils.models import UploadFilepathFactory

# class UserType(enum):
#     """The type of user object."""

#     NORMAL = "normal"
#     AGENT = "agent"


class UserManager(BaseUserManager, ManagerBase["User"]):
    """Manager for users."""

    def create(self, **kwargs):
        return self.create_user(**kwargs)

    def create_user(self, email, password=None, username=None, **extra_fields):
        """Create, save, and return a new user. Add user to base group."""
        if not email:
            raise ValueError("User must have an email address")

        email = self.normalize_email(email)

        if username is None:
            username = email

        name = extra_fields.pop("name", None)
        phone = extra_fields.pop("phone", None)

        user: User = self.model(username=username, email=email, **extra_fields)

        if password:
            user.set_password(password)
            user.is_active = True
        else:
            user.set_unusable_password()
            user.is_active = False

        user.save(using=self._db)

        Profile.objects.create(
            user=user,
            name=name,
            phone=phone,
        )
        user.save(using=self._db)  # Set default profile image, etc

        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and return a new superuser."""
        user = self.create_user(email, password, **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user

    def create_adminuser(self, email, password, **extra_fields):
        """Create and return a new admin user."""
        user = self.create_user(email, password, **extra_fields)
        user.is_staff = True
        user.is_superuser = False
        user.save(using=self._db)

        return user

    def get_or_create(self, defaults=None, **kwargs):
        """Return user if they exist, or create a new one if not."""

        query = self.filter(**kwargs)
        if query.exists() and query.count() == 1:
            return query.first(), False
        elif query.count() > 1:
            raise User.MultipleObjectsReturned(
                f"Expected 1 user, but returned {query.count()}!"
            )
        else:
            defaults = defaults or {}
            return self.create(**defaults, **kwargs), True


class User(AbstractBaseUser, PermissionsMixin, UniqueModel):
    """User model for system."""

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    email = models.EmailField(max_length=64, unique=True, null=True, blank=True)
    username = models.CharField(max_length=64, unique=True, blank=True)
    password = models.CharField(_("password"), max_length=128, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True, editable=False, blank=True)
    date_modified = models.DateTimeField(auto_now=True, editable=False, blank=True)

    # is_onboarded = models.BooleanField(default=False)

    clubs = models.ManyToManyField(
        "clubs.Club", through="clubs.ClubMembership", blank=True
    )

    USERNAME_FIELD = "username"

    objects: ClassVar[UserManager] = UserManager()

    # Foreign Relationships
    profile: Optional["Profile"]
    club_memberships: models.QuerySet
    team_memberships: models.QuerySet
    socials: models.QuerySet["SocialProfile"]
    verified_emails: models.QuerySet["VerifiedEmail"]

    # Dynamic Properties
    @property
    def name(self) -> str:
        return self.profile.name

    @property
    def is_email_verified(self):
        return self.verified_emails.filter(email=self.email).exists()

    @property
    def can_authenticate(self) -> bool:
        """See if this user has a way to authenticate with the server."""
        return self.has_usable_password() or self.socialaccount_set.count() > 0

    @property
    def is_useragent(self):
        return getattr(self, "useragent", None) is not None

    @property
    def is_onboarded(self) -> bool:
        return (
            self.club_memberships.count() > 0
            and self.profile is not None
            and self.profile.name is not None
        )

    # Overrides
    def __str__(self):
        return self.username

    def clean(self):
        # If user is created through some other method, ensure username is set.
        if self.username is None or self.username == "":
            self.username = self.email
        return super().clean()

    def has_perm(self, perm, obj=None, is_global=False):
        # Allow checking permissions from a global context, meaning
        # the user has this permission for all objects (like a staff member).
        # Adapted from:
        # https://github.com/django/django/blob/485f483d49144a2ea5401442bc3b937a370b3ca6/django/contrib/auth/models.py#L261
        if is_global:
            for backend in auth.get_backends():
                if not hasattr(backend, "has_global_perm"):
                    continue
                try:
                    if backend.has_global_perm(self, perm):
                        return True
                    else:
                        return False
                except PermissionDenied:
                    return False

        return super().has_perm(perm, obj)


class Profile(ModelBase):
    """User information."""

    get_user_profile_filepath = UploadFilepathFactory("users/profiles/")

    user = models.OneToOneField(
        User, primary_key=True, related_name="profile", on_delete=models.CASCADE
    )

    image = models.ImageField(
        upload_to=get_user_profile_filepath,
        null=True,
        blank=True,
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=2, blank=True, null=True)
    country = CountryField(null=True, blank=True)

    birthday = models.DateField(null=True, blank=True)

    school_email = models.EmailField(blank=True, null=True)
    graduation_year = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1900), MaxValueValidator(3000)],
    )
    major = models.CharField(blank=True, null=True, max_length=128)
    bio = models.TextField(null=True, blank=True)

    # Dynamic Properties
    @property
    def email(self):
        return self.user.email

    @property
    def is_school_email_verified(self):
        return self.user.verified_emails.filter(email=self.school_email).exists()

    def __str__(self):
        return self.name or self.user.username

    # Overrides
    class Meta:
        _is_unique_nonempty_phone = models.Q(
            models.Q(phone__isnull=False) & ~models.Q(phone__exact="")
        )

        # Ensure non-empty phone fields are unique
        constraints = [
            models.UniqueConstraint(
                fields=("phone",),
                condition=_is_unique_nonempty_phone,
                name="Unique non-null phone number for each profile",
            )
        ]

        # Allow non-empty phone fields to be easily searchable
        indexes = [
            models.Index(
                fields=("phone",), name="phone_idx", condition=_is_unique_nonempty_phone
            )
        ]


class SocialProfile(SocialProfileBase):
    """A user's social media links."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="socials")


class UserAgentManager(BaseUserManager):
    """Manage user agent objects."""

    def create(self, username: str, apikey_type: "ApiKeyType", **kwargs):
        return super().create(username=username, apikey_type=apikey_type, **kwargs)


class ApiKeyType(models.TextChoices):
    """What type of api key is attached to the user agent."""

    CLUB = "club", _("Club Api Key")


class UserAgent(User):
    """
    Non-person user of the system.

    This can be used to represent requests made by external clients
    that don't necessarily represent an individual person.
    """

    apikey_type = models.CharField(choices=ApiKeyType.choices)

    # Foreign Relationships
    club_apikey: Optional[models.Model]

    # Overrides
    objects: ClassVar[UserAgentManager] = UserAgentManager()

    @property
    def can_authenticate(self):
        return False

    @property
    def is_useragent(self):
        return True


def generate_verification_code():
    """Get a unique verification code."""
    characters = string.ascii_uppercase + string.digits

    # Keep regenerating code until unique
    while True:
        code = "".join(random.choices(characters, k=6))

        if not EmailVerificationCode.objects.filter(code=code).exists():
            return code


def generate_verification_expiry():
    """Generate expiration time for verification code."""

    return timezone.now() + timezone.timedelta(minutes=15)


class EmailVerificationCode(ModelBase):
    """Store and track code used for email verification."""

    code = models.CharField(
        unique=True,
        max_length=6,
        default=generate_verification_code,
        # editable=False,
    )
    email = models.EmailField()
    expires_at = models.DateTimeField(
        default=generate_verification_expiry, editable=False
    )

    @property
    def is_expired(self):
        return self.expires_at < timezone.now()


class VerifiedEmail(ModelBase):
    """User has verified this email."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verified_emails"
    )
    email = models.EmailField(editable=False, unique=True)

    def __str__(self):
        return self.email
