from typing import Optional

from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import BadRequest, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import models
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlencode, urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.authtoken.models import Token

from app.settings import BASE_URL, DEFAULT_AUTH_BACKEND, DEFAULT_FROM_EMAIL
from core.abstracts.services import ServiceBase
from lib.emails import send_html_mail
from users.models import EmailVerificationCode, User, VerifiedEmail
from utils.helpers import get_client_url, get_full_url


class UserService(ServiceBase[User]):
    """Manage business logic for users domain."""

    @classmethod
    def get_from_token(cls, token: str):
        token = Token.objects.get(key=token)
        return cls(token.user)

    @classmethod
    def register_user(cls, email: str, password: str, name=None):
        """Create a new user in the database."""

        user = User.objects.create_user(email=email, password=password, name=name)

        return user

    @classmethod
    def login_user(cls, request: HttpRequest, user: User):
        """Creates a new user session."""

        return cls(user).login(request)

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

    def login(self, request):
        """Creates a new user session."""

        return login(request, self.obj, backend=DEFAULT_AUTH_BACKEND)

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

    def send_account_setup_link(
        self, next_url: Optional[str] = None, send_to_client=True
    ):
        """Send link to user for setting up account."""

        uidb64 = urlsafe_base64_encode(force_bytes(self.obj.pk))
        code = default_token_generator.make_token(self.obj)

        if send_to_client:
            url = get_client_url(f"account-setup/?uidb64={uidb64}&code={code}")
        else:
            url = get_full_url(
                # reverse(
                #     "users:verify_setup_account",
                #     kwargs={"uidb64": uidb64, "token": code},
                # )
                reverse(
                    "users-auth:resetpassword_confirm",
                    kwargs={"uidb64": uidb64, "token": code},
                )
            )

        if next_url:
            url += "?" + urlencode({"next": next_url})

        send_html_mail(
            "Finish account setup",
            to=[self.obj.email],
            html_template="users/setup_account_email.html",
            html_context={"setup_url": url},
        )

    @classmethod
    def verify_account_setup_token(cls, uidb64: str, code: str, set_user_active=True):
        """Verify a user id and token pair."""

        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_object_or_404(User, pk=uid)

        if not default_token_generator.check_token(user, code):
            raise BadRequest("Invalid request")

        if not user.is_active and set_user_active:
            user.is_active = True
            user.save()

        return user

    def send_verification_code(self, email: str):
        """Send verification code to email."""

        validate_email(email)

        if self.obj.verified_emails.filter(email=email).exists():
            raise BadRequest(f"Email {email} is already verified for user.")
        elif VerifiedEmail.objects.filter(email=email).exclude(user=self.obj).exists():
            raise BadRequest(f"Email {email} is already verified by another user.")
        elif (
            User.objects.filter(
                models.Q(email=email) | models.Q(profile__school_email=email)
            )
            .exclude(id=self.obj.id)
            .exists()
        ):
            raise BadRequest(f"Email {email} is already taken.")

        verification = EmailVerificationCode.objects.create(email=email)

        send_mail(
            subject="Verification Code",
            message=f"Verification code: {verification.code}",
            from_email=DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

    def check_verification_code(self, email: str, code: str, raise_exception=True):
        """Verify code sent to email."""

        verification = EmailVerificationCode.objects.filter(
            email=email, code__exact=code
        )

        if not verification.exists():
            if raise_exception:
                raise BadRequest("Invalid verification code.")
            else:
                return False

        verification = verification.first()
        if verification.is_expired:
            if raise_exception:
                raise BadRequest("Verification code expired.")
            else:
                return False

        # Verification was successful, clean up previous codes
        EmailVerificationCode.objects.filter(email=email).delete()
        VerifiedEmail.objects.create(email=email, user=self.obj)

        return True
