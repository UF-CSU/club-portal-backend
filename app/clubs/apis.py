from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register("clubs", viewsets.ClubViewSet, basename="club")
router.register("club-previews", viewsets.ClubPreviewViewSet, basename="clubpreview")
router.register(
    r"clubs/(?P<club_id>\d+)/members",
    viewsets.ClubMemberViewSet,
    basename="clubmember",
)
router.register(
    r"clubs/(?P<club_id>.+)/members/person",
    viewsets.ClubMembershipSingleViewSet,
    basename="clubmembership",
)
router.register(
    r"clubs/(?P<club_id>\d+)/roles",
    viewsets.ClubRoleViewSet,
    basename="clubrole",
)
router.register(r"clubs/(?P<club_id>.+)/teams", viewsets.TeamViewSet, basename="team")
router.register(
    r"clubs/(?P<club_id>.+)/teams/(?P<team_id>.+)/members",
    viewsets.TeamMemberViewSet,
    basename="teammember",
)
router.register(
    r"clubs/(?P<club_id>\d+)/teams/(?P<team_id>.+)/roles",
    viewsets.TeamRoleViewSet,
    basename="teamrole",
)
router.register(
    r"clubs/(?P<club_id>.+)/apikeys", viewsets.ClubApiKeyViewSet, basename="apikey"
)
router.register(
    r"clubs/(?P<club_id>.+)/files", viewsets.ClubFilesViewSet, basename="file"
)
router.register(
    "club-memberships",
    viewsets.UserClubMembershipsViewSet,
    basename="user_clubmembership",
)
router.register("tags", viewsets.ClubTagsViewSet, basename="clubtag")


app_name = "api-clubs"

urlpatterns = [
    path("clubs/join/", viewsets.JoinClubsViewSet.as_view(), name="join"),
    path("clubs/follow/", viewsets.FollowClubsViewSet.as_view(), name="follow"),
    path("", include(router.urls)),
    path(
        "clubs/<int:id>/invite/",
        viewsets.InviteClubMemberView.as_view(),
        name="clubinvite",
    ),
    path(
        "clubs/<int:club_id>/teams/<int:team_id>/invite/",
        viewsets.InviteTeamMemberView.as_view(),
        name="teaminvite",
    ),
]
