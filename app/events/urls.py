from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "events"

urlpatterns = [
    path(
        "events/<int:id>/attendance/",
        views.record_attendance_view,
        name="attendance",
    ),
    path(
        "events/<int:id>/attendance/done/",
        TemplateView.as_view(
            template_name="events/attendance_done.html",
        ),
        name="attendance_done",
    ),
    path(
        "events/download/event/<int:id>/",
        views.download_event_calendar,
        name="eventcalendar",
    ),
    path(
        "events/download/club/<int:club_id>/",
        views.download_club_calendar,
        name="eventcalendar_club",
    ),
]
