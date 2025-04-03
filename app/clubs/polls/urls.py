from django.urls import path

from clubs.polls import views

app_name = "polls"

urlpatterns = [
    path("poll/<int:poll_id>/", views.show_poll_view, name="poll"),
    path("poll/<int:poll_id>/success/", views.poll_success_view, name="poll_success"),
]
