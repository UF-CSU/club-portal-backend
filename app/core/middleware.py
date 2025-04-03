import zoneinfo

from django.http import HttpRequest
from django.utils import timezone

from core.abstracts.middleware import BaseMiddleware


class TimezoneMiddleware(BaseMiddleware):
    """
    Convert dates to local user timezone.

    Ref: https://docs.djangoproject.com/en/5.1/topics/i18n/timezones/
    """

    def on_request(self, request: HttpRequest, *args, **kwargs):
        tzname = request.session.get("django_timezone")

        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()

        return super().on_request(request, *args, **kwargs)
