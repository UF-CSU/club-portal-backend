from django.urls import include, path
from django.views.generic import TemplateView

from . import views

app_name = "clubs"

urlpatterns = [
    path("available/", views.available_clubs_view, name="available"),
    path("links/<int:link_id>/", views.club_home_view, name="link"),
    path("club/<int:club_id>/", views.club_home_view, name="home"),
    path("club/<int:club_id>/join/", views.join_club_view, name="join"),
    path(
        "club/<int:club_id>/event/<int:event_id>/join/",
        views.record_attendance_view,
        name="joinevent",
    ),
    path(
        "club/<int:club_id>/event/<int:event_id>/done/",
        TemplateView.as_view(
            template_name="clubs/join_event_done.html",
        ),
        name="joinevent_done",
    ),
    path(
        "club/<int:club_id>/event/<int:event_id>/calendar/",
        views.download_event_calendar,
        name="eventcalendar",
    ),
    path(
        "club/<int:club_id>/calendar/",
        views.download_club_calendar,
        name="eventcalendar_club",
    ),
    path("polls/", include("clubs.polls.urls")),
]
