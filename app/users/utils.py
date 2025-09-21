from django.core import exceptions
from django.core.validators import validate_email

from app.settings import SCHOOL_EMAIL_DOMAIN


def is_school_email(email: str):
    """Check if the supplied email address is a valid school email."""

    try:
        validate_email(email)
        return email.endswith(SCHOOL_EMAIL_DOMAIN)
    except exceptions.ValidationError:
        return False
