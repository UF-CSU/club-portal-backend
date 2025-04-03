from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register("clubs", viewsets.ClubViewSet, basename="club")
router.register(
    r"clubs/(?P<club_id>.+)/members",
    viewsets.ClubMembershipViewSet,
    basename="club-members",
)

app_name = "api-clubs"

urlpatterns = [
    path("", include(router.urls)),
    path(
        "clubs/<int:id>/invite/", viewsets.InviteClubMemberView.as_view(), name="invite"
    ),
]
