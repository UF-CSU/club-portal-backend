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

router.register(
    r"clubs/(?P<club_id>.+)/members/person",
    viewsets.ClubMemberViewSet,
    basename="clubmembership",
)

router.register("clubs/(?P<club_id>.+)/teams", viewsets.TeamViewSet, basename="team")
router.register(
    "clubs/(?P<club_id>.+)/apikeys", viewsets.ClubApiKeyViewSet, basename="apikey"
)

router.register("club-previews", viewsets.ClubPreviewViewSet, basename="clubpreview")
router.register(r"clubs/(?P<club_id>.+)/files", viewsets.ClubFilesViewSet, basename="file")

app_name = "api-clubs"

urlpatterns = [
    path("clubs/join/", viewsets.JoinClubsViewSet.as_view(), name="join"),
    path("", include(router.urls)),
    path(
        "clubs/<int:id>/invite/", viewsets.InviteClubMemberView.as_view(), name="invite"
    ),
    path("tags/", viewsets.ClubTagsView.as_view(), name="tags"),
]
