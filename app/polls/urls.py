from django.urls import path

from polls import views

app_name = "polls"

urlpatterns = [
    path("poll/<int:poll_id>/", views.show_poll_view, name="poll"),
    path("poll/<int:poll_id>/success/", views.poll_success_view, name="poll_success"),
    path(
        "poll/<int:poll_id>/submissions/",
        views.download_submissions,
        name="poll_submissions",
    ),
    path(
        "poll/<int:poll_id>/analytics/", views.get_poll_analytics, name="poll_analytics"
    ),
]
