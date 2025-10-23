from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/polls/(?P<poll_id>\d+)/submissions/$",
        consumers.PollSubmissionConsumer.as_asgi(),
    ),
]
