"""
URL Patterns for users REST API.
"""

from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from users import viewsets

router = DefaultRouter()
router.register("users", viewsets.UserViewSet, basename="user")
router.register(
    "verification", viewsets.EmailVerificationViewSet, basename="verification"
)
router.register("users", viewsets.PublicUserViewSet, basename="public_user")

app_name = "api-users"

urlpatterns = [
    path("", include(router.urls)),
    path("login/", RedirectView.as_view(url=reverse_lazy("api-users:login"))),
    path(
        "token/",
        viewsets.AuthTokenView.as_view({"get": "retrieve", "post": "post"}),
        name="login",
    ),
    path("ticket/", viewsets.TicketView.as_view()),
    path("me/", viewsets.ManageUserView.as_view(), name="me"),
    path("me/calendar/", viewsets.ExportUserCalendarView.as_view(), name="calendar"),
    path("oauth-directory/", viewsets.OauthDirectoryView.as_view()),
    path("me/providers/", viewsets.SocialProviderViewSet.as_view({"get": "list"})),
    path(
        "oauth/provider/",
        viewsets.RedirectToProviderView.as_view(),
        name="oauth_redirect",
    ),
    path(
        "oauth/provider/redirect/",
        viewsets.ReturnFromOauthView.as_view(),
        name="oauth_return",
    ),
]
