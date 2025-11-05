from allauth.account.adapter import DefaultAccountAdapter
from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import Provider
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from django.http import HttpRequest

from users.models import User

ProviderType = Provider
OauthProviderType = OAuth2Provider


class CustomHeadlessAdapter(DefaultHeadlessAdapter):
    pass


class CustomAccountAdapter(DefaultAccountAdapter):
    pass


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def __init__(self, request=None):
        super().__init__(request)

        self.error_messages["user_already_exists"] = (
            "Account exists with this email, but oauth has not been setup."
        )

    def populate_user(self, request: HttpRequest, sociallogin, data):
        email = data.get("email")

        existing_user = User.objects.find_by_email(email=email)
        if existing_user:
            # raise exceptions.AuthenticationFailed(detail=f"User already exists with email {email}")
            return self.validation_error("user_already_exists")

        return super().populate_user(request, sociallogin, data)


__all__ = ["ProviderType", "OauthProviderType"]
