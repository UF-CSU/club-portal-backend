from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/analytics/(?P<link_id>\d+)/linkvisits/$",
        consumers.LinkVisitConsumer.as_asgi(),
    ),
]
