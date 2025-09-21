import random
from typing import Optional

from django.urls import reverse

from lib.faker import fake
from users.models import User
from utils.helpers import reverse_query

SEND_EMAIL_VERIFICATION_URL = reverse("api-users:verification-list")
CHECK_EMAIL_VERIFICATION_URL = reverse("api-users:verification-check")


def create_test_adminuser(**kwargs):
    """
    Create Test Admin User

    Used to create unique admin users quickly for testing, it will return
    admin user with test data.
    """
    prefix = random.randint(0, 500)
    email = f"{prefix}-admin@example.com"
    password = "testpass"

    return User.objects.create_adminuser(email=email, password=password, **kwargs)


def create_test_user(profile: Optional[dict] = None, **kwargs):
    """Create user for testing purposes."""

    payload = {
        "name": fake.name(),
        "email": fake.safe_email(),
        "password": fake.password(15),
        **kwargs,
    }

    user = User.objects.create_user(**payload)

    if not profile:
        return user

    for key, value in profile.items():
        setattr(user.profile, key, value)

    user.profile.save()
    return user


def create_test_users(count=5, **kwargs):
    """Create multiple test users."""

    ids = [create_test_user(**kwargs).id for _ in range(count)]
    return User.objects.filter(id__in=ids).all()


def register_user_url():
    """Get user register url."""

    return reverse_query("users:register")


def login_user_url():
    """Get user login url."""

    return reverse("users-auth:login")
