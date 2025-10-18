import zoneinfo

from asgiref.sync import sync_to_async
from channels.sessions import CookieMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.authtoken.models import Token

from app import settings
from core.abstracts.middleware import BaseMiddleware


class TimezoneMiddleware(BaseMiddleware):
    """
    Convert dates to local user timezone.

    Ref: https://docs.djangoproject.com/en/5.1/topics/i18n/timezones/
    """

    async def on_request(self, request: HttpRequest, *args, **kwargs):
        tzname = request.COOKIES.get("user_timezone", "UTC")
        timezone.activate(zoneinfo.ZoneInfo(tzname))

        return await super().on_request(request, *args, **kwargs)


"""
Ref: https://gist.github.com/J-Priebe/58fda441698536d64e04781d9214e1db
"""


class WebSocketMiddleware:
    """
    Custom middleware for Token authentication. Must be wrapped in CookieMiddleware.
    Adds user to scope if they have a valid token.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        await sync_to_async(close_old_connections)()

        # cookies are in scope, since we're wrapped in CookieMiddleware
        cookie = scope["cookies"].get(settings.AUTH_TOKEN_KEY)

        if not cookie:
            scope["user"] = AnonymousUser()
        else:
            try:
                token = await sync_to_async(Token.objects.select_related("user").get)(
                    key=cookie
                )
                scope["user"] = token.user
            except Token.DoesNotExist:
                scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)


def WebSocketMiddlewareStack(inner):
    """
    Handy shortcut to ensure we're wrapped in CookieMiddleware.
    """
    return CookieMiddleware(WebSocketMiddleware(inner))
