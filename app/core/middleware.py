import zoneinfo

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.http import HttpRequest
from django.utils import timezone

from core.abstracts.middleware import BaseMiddleware
from users.models import Ticket


class TimezoneMiddleware(BaseMiddleware):
    """
    Convert dates to local user timezone.

    Ref: https://docs.djangoproject.com/en/5.1/topics/i18n/timezones/
    """

    async def on_request(self, request: HttpRequest, *args, **kwargs):
        tzname = request.COOKIES.get("user_timezone", "UTC")
        timezone.activate(zoneinfo.ZoneInfo(tzname))

        return await super().on_request(request, *args, **kwargs)


class WebSocketMiddleware:
    """
    Custom middleware for WebSocket authentication. Implements ticket-based auth.
    Ref: https://devcenter.heroku.com/articles/websocket-security
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        await sync_to_async(close_old_connections)()

        subprotocols = scope["subprotocols"]  # ["Authorization", "<ticket>"]

        if len(subprotocols) != 2 or subprotocols[0] != "Authorization":
            scope["user"] = AnonymousUser()
        else:
            key = subprotocols[1]

            try:
                ticket = await sync_to_async(Ticket.objects.select_related("user").get)(
                    key=key
                )
                scope["user"] = ticket.user
                await sync_to_async(ticket.delete)()
            except Ticket.DoesNotExist:
                scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
