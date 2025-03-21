"""
URL Patterns for users REST API.
"""

from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

from users import viewsets

app_name = "api-users"

urlpatterns = [
    path("login/", RedirectView.as_view(url=reverse_lazy("api-users:login"))),
    path(
        "token/",
        viewsets.AuthTokenView.as_view({"get": "retrieve", "post": "post"}),
        name="login",
    ),
    path("me/", viewsets.ManageUserView.as_view(), name="me"),
    path(
        "users/",
        include(
            [
                path("create/", viewsets.CreateUserView.as_view(), name="create"),
            ]
        ),
    ),
    path("oauth-directory/", viewsets.OauthDirectoryView.as_view()),
]
