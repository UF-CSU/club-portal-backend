"""
User Models.
"""

from typing import ClassVar, Optional

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.abstracts.models import ManagerBase, ModelBase, UniqueModel
from utils.models import UploadFilepathFactory


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
        else:
            user.set_unusable_password()

        user.is_active = True
        user.save(using=self._db)

        Profile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

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

    def create_random_password(self):
        """Create and return a random password."""
        return self.make_random_password()


class User(AbstractBaseUser, PermissionsMixin, UniqueModel):
    """User model for system."""

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    email = models.EmailField(max_length=32, unique=True)
    username = models.CharField(max_length=32, unique=True, blank=True)
    password = models.CharField(_("password"), max_length=128, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True, editable=False, blank=True)
    date_modified = models.DateTimeField(auto_now=True, editable=False, blank=True)

    USERNAME_FIELD = "username"

    objects: ClassVar[UserManager] = UserManager()

    # Foreign Relationships
    profile: Optional["Profile"]
    club_memberships: models.QuerySet
    team_memberships: models.QuerySet

    # Dynamic Properties
    @property
    def first_name(self):
        if not self.profile:
            return None

        return self.profile.first_name

    @property
    def last_name(self):
        if not self.profile:
            return None

        return self.profile.last_name

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

    # email = models.EmailField(max_length=128, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)

    address_1 = models.CharField(max_length=255, null=True, blank=True)
    address_2 = models.CharField(max_length=255, null=True, blank=True)

    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=2, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)

    birthday = models.DateField(null=True, blank=True)

    # TODO: Avatar?
    image = models.ImageField(
        upload_to=get_user_profile_filepath,
        default="user/profile.jpeg",
        blank=True,
    )

    @property
    def name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    # Dynamic Properties
    @property
    def email(self):
        return self.user.email

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
