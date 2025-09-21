from typing import Optional

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import BadRequest, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import models, transaction
from django.forms import model_to_dict
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlencode, urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.authtoken.models import Token

from app.settings import BASE_URL, DEFAULT_AUTH_BACKEND, DEFAULT_FROM_EMAIL
from clubs.models import ClubMembership, TeamMembership
from core.abstracts.services import ServiceBase
from lib.emails import send_html_mail
from polls.models import PollSubmission
from users.models import EmailVerificationCode, User, VerifiedEmail
from users.utils import is_school_email
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

    @classmethod
    def merge_users(cls, users: models.QuerySet[User] | list[User]):
        """Combine multiple user objects."""

        if isinstance(users, list):
            ids = [user.id for user in users]
            users = User.objects.filter(id__in=ids)

        users = users.order_by("id")
        oldest_user = users.first()
        other_users = users.exclude(id=oldest_user.id)

        if not other_users.exists():
            return oldest_user

        # If there's any issues, revert everything
        with transaction.atomic():
            # Merge info from other users
            for user in other_users:
                # Merge profile info
                profile_info = model_to_dict(user.profile)
                for key, value in profile_info.items():
                    if (
                        value is not None
                        and getattr(oldest_user.profile, key, None) is None
                    ):
                        setattr(oldest_user.profile, key, value)

                # If oldest has school email as personal, and other user has personal email as personal,
                # change personal on oldest user
                if is_school_email(oldest_user.email) and not is_school_email(
                    user.email
                ):
                    oldest_user.email = user.email

                # Merge relationships
                Token.objects.filter(user=user).update(user=oldest_user)
                VerifiedEmail.objects.filter(user=user).update(user=oldest_user)
                PollSubmission.objects.filter(user=user).update(user=oldest_user)
                SocialAccount.objects.filter(user=user).update(user=oldest_user)

                # Merge memberships
                oldest_user_clubs = oldest_user.clubs.values_list("id", flat=True)
                oldest_user_teams = oldest_user.teams.values_list("id", flat=True)
                ClubMembership.objects.filter(user=user).exclude(
                    club__id__in=oldest_user_clubs
                ).update(user=oldest_user)
                TeamMembership.objects.filter(user=user).exclude(
                    team__id__in=oldest_user_teams
                ).update(user=oldest_user)

            # Delete other users
            other_users.delete()

            # Save user info
            oldest_user.profile.save()
            oldest_user.save()

        return oldest_user

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
        # elif VerifiedEmail.objects.filter(email=email).exclude(user=self.obj).exists():
        #     raise BadRequest(f"Email {email} is already verified by another user.")
        # elif (
        #     User.objects.filter(
        #         models.Q(email=email) | models.Q(profile__school_email=email)
        #     )
        #     .exclude(id=self.obj.id)
        #     .exists()
        # ):
        #     raise BadRequest(f"Email {email} is already taken.")

        # Delete existing codes
        EmailVerificationCode.objects.filter(email=email).delete()

        # Create new code
        verification = EmailVerificationCode.objects.create(email=email)

        send_mail(
            subject="Verification Code",
            message=f"Verification code: {verification.code}",
            from_email=DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

    def check_verification_code(self, email: str, code: str, raise_exception=True):
        """Verify code sent to email."""

        user = self.obj

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

        # Check for existing verified emails

        # Check for existing users, merge accounts
        existing_user = User.objects.find_by_email(email=email)
        if existing_user and existing_user.id != user.id:
            user = UserService.merge_users(users=[user, existing_user])

        # Verification was successful, clean up previous codes
        EmailVerificationCode.objects.filter(email=email).delete()
        VerifiedEmail.objects.create(email=email, user=user)

        return True
