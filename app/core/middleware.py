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
        tzname = request.COOKIES.get("user_timezone", "UTC")
        timezone.activate(zoneinfo.ZoneInfo(tzname))

        return super().on_request(request, *args, **kwargs)


# class TokenAuthMiddleware(BaseMiddleware):
#     """
#     Manually set user based on DRF token.

#     This was added to patch an issue where allauth wouldn't recognize the
#     user as logged in, and wasn't able to add a provider for a user. This
#     should be switched out for a better method.
#     """

#     def on_request(self, request, *args, **kwargs):
#         token_str = request.COOKIES.get("clubportal-token", None)
#         if token_str is not None:
#             try:
#                 token = Token.objects.get(key=token_str)
#                 request.user = token.user
#             except Token.DoesNotExist:
#                 pass

#         return super().on_request(request, *args, **kwargs)
