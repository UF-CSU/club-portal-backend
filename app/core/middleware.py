import zoneinfo

from django.http import HttpRequest
from django.utils import timezone

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
