from allauth.account.adapter import DefaultAccountAdapter
from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import Provider
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

ProviderType = Provider
OauthProviderType = OAuth2Provider


class CustomHeadlessAdapter(DefaultHeadlessAdapter):
    pass


class CustomAccountAdapter(DefaultAccountAdapter):
    pass


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    pass


__all__ = ["ProviderType", "OauthProviderType"]
