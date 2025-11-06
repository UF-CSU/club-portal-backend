from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/querycsv/(?P<job_id>\d+)/querycsv/$",
        consumers.QueryCsvConsumer.as_asgi(),
    ),
]
