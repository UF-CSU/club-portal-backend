import random

from django.urls import reverse

from lib.faker import fake
from users.models import User
from utils.helpers import reverse_query


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


def create_test_user(**kwargs):
    """Create user for testing purposes."""

    payload = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.safe_email(),
        "password": fake.password(15),
        **kwargs,
    }

    return User.objects.create_user(**payload)


def register_user_url():
    """Get user register url."""

    return reverse_query("users:register")


def login_user_url():
    """Get user login url."""

    return reverse("users-auth:login")
