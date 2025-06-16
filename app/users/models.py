"""
User Models.
"""

from typing import ClassVar, Optional

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import MinValueValidator
from django.db import models
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

        first_name = extra_fields.pop("first_name", None)
        last_name = extra_fields.pop("last_name", None)
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
            first_name=first_name,
            last_name=last_name,
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

    # Dynamic Properties
    @property
    def first_name(self):
        if self.profile is None:
            return None

        return self.profile.first_name

    @first_name.setter
    def first_name(self, value):
        Profile.objects.update_or_create(defaults={"user": self}, first_name=value)

    @property
    def last_name(self):
        if self.profile is None:
            return None

        return self.profile.last_name

    @last_name.setter
    def last_name(self, value):
        Profile.objects.update_or_create(defaults={"user": self}, last_name=value)

    @property
    def can_authenticate(self):
        """See if this user has a way to authenticate with the server."""
        return self.has_usable_password() or self.socialaccount_set.count() > 0

    @property
    def display(self):
        """Display name."""
        return self.profile.display

    @property
    def is_useragent(self):
        return False

    # Overrides
    def __str__(self):
        return self.username

    def clean(self):
        # If user is created through some other method, ensure username is set.
        if self.username is None or self.username == "":
            self.username = self.email
        return super().clean()


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

    first_name = models.CharField(max_length=255, blank=True, null=True)
    middle_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    prefix = models.CharField(
        max_length=255, blank=True, null=True, help_text="Mr/Mrs/Dr/etc"
    )
    nickname = models.CharField(max_length=255, blank=True, null=True)

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

    display = models.CharField(
        blank=True,
        max_length=128,
        null=True,
        help_text="Name to use when displaying the user.",
    )

    @property
    def name(self):
        return f"{self.prefix or ''} {self.first_name or ''} {self.last_name or ''}".strip()

    # Dynamic Properties
    @property
    def email(self):
        return self.user.email

    def __str__(self):
        return self.display

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

    def save(self, *args, **kwargs):
        if self.display is None or self.display.strip() == "":
            if self.name is not None and len(self.name) > 0:
                self.display = self.name
            else:
                self.display = self.user.email.split("@")[0]

        return super().save(*args, **kwargs)


class SocialProfile(SocialProfileBase):
    """A user's social media links."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="socials")


class UserAgentManager(BaseUserManager):
    """Manage user agent objects."""

    def create(self, username: str, apikey_type: "KeyType", **kwargs):
        return super().create(username=username, apikey_type=apikey_type, **kwargs)


class KeyType(models.TextChoices):
    """What type of api key is attached to the user agent."""

    CLUB = "club", _("Club Api Key")


class UserAgent(User):
    """
    Non-person user of the system.

    This can be used to represent requests made by external clients
    that don't necessarily represent an individual person.
    """

    apikey_type = models.CharField(choices=KeyType.choices)

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
