from django.urls import include, path

from . import views

app_name = "clubs"

urlpatterns = [
    path("available/", views.available_clubs_view, name="available"),
    path("links/<int:link_id>/", views.club_home_view, name="link"),
    path("club/<int:club_id>/", views.club_home_view, name="home"),
    path("club/<int:club_id>/join/", views.join_club_view, name="join"),
    path("polls/", include("clubs.polls.urls")),
    # path("accept-invite/<int:user_id>/", views.accept_invite, name="accept-invite"),
]
