"""
URL Patterns for users REST API.
"""

from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from users import viewsets

router = DefaultRouter()
router.register("users", viewsets.UserViewSet, basename="user")

app_name = "api-users"

urlpatterns = [
    path("", include(router.urls)),
    path("login/", RedirectView.as_view(url=reverse_lazy("api-users:login"))),
    path(
        "token/",
        viewsets.AuthTokenView.as_view({"get": "retrieve", "post": "post"}),
        name="login",
    ),
    path("me/", viewsets.ManageUserView.as_view(), name="me"),
    # TODO: Configure security around creating users
    # path(
    #     "users/",
    #     include(
    #         [
    #             path("create/", viewsets.CreateUserView.as_view(), name="create"),
    #         ]
    #     ),
    # ),
    path("oauth-directory/", viewsets.OauthDirectoryView.as_view()),
]
