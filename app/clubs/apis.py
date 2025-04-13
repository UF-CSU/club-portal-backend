from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register("clubs", viewsets.ClubViewSet, basename="club")
router.register(
    r"clubs/(?P<club_id>.+)/members",
    viewsets.ClubMembershipViewSet,
    basename="clubmember",
)
router.register("clubs/(?P<club_id>.+)/teams", viewsets.TeamViewSet, basename="team")
router.register(
    "clubs/(?P<club_id>.+)/apikeys", viewsets.ClubApiKeyViewSet, basename="apikey"
)

app_name = "api-clubs"

urlpatterns = [
    path("", include(router.urls)),
    path(
        "clubs/<int:id>/invite/", viewsets.InviteClubMemberView.as_view(), name="invite"
    ),
]
