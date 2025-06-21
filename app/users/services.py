from typing import Optional

from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlencode, urlsafe_base64_encode

from app.settings import BASE_URL, DEFAULT_AUTH_BACKEND, DEFAULT_FROM_EMAIL
from core.abstracts.services import ServiceBase
from lib.emails import send_html_mail
from users.models import User
from utils.helpers import get_full_url


class UserService(ServiceBase[User]):
    """Manage business logic for users domain."""

    @classmethod
    def register_user(cls, email: str, password: str, name=None):
        """Create a new user in the database."""

        user = User.objects.create_user(email=email, password=password, name=name)

        return user

    @classmethod
    def login_user(cls, request: HttpRequest, user: User):
        """Creates a new user session."""

        return login(request, user, backend=DEFAULT_AUTH_BACKEND)

    @classmethod
    def authenticate_user(
        cls, request: HttpRequest, username_or_email: str, password: str
    ) -> User:
        """Verify user credentials, return user if valid."""

        if "@" in username_or_email:
            user = User.objects.get(profile__email=username_or_email)
        else:
            user = User.objects.get(username=username_or_email)

        auth_user = authenticate(request, username=user.username, password=password)

        if auth_user is None:
            raise ValidationError("Invalid user credentials.")

        return user

    def send_password_reset(self):
        """Send password reset email."""

        user_email = self.obj.email

        protocol, domain = BASE_URL.split("://")
        domain = domain.split("/")[0]

        context = {
            "email": user_email,
            "domain": domain,
            "site_name": domain,
            "uid": urlsafe_base64_encode(force_bytes(self.obj.pk)),
            "user": self.obj,
            "token": default_token_generator.make_token(self.obj),
            "protocol": protocol,
        }

        send_html_mail(
            subject=f"Password reset on {domain}",
            html_template="users/authentication/reset_pass_email.html",
            html_context=context,
            to=[self.obj.email],
        )

    def send_account_setup_link(self, next_url: Optional[str] = None):
        """Send link to user for setting up account."""

        url = get_full_url(
            reverse(
                "users:verify_setup_account",
                kwargs={
                    "uidb64": urlsafe_base64_encode(force_bytes(self.obj.pk)),
                    "token": default_token_generator.make_token(self.obj),
                },
            )
        )

        if next_url:
            url += "?" + urlencode({"next": next_url})

        send_mail(
            "Finish account setup",
            message=f"Click here: {url}",
            from_email=DEFAULT_FROM_EMAIL,
            recipient_list=[self.obj.email],
            fail_silently=False,
        )
