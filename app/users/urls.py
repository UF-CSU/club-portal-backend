"""
URL mappings for the user API.
"""

from django.urls import path

from users import views

app_name = "users"

# Note: Login and authentication is handled by users.authentication
urlpatterns = [
    path("register/", views.register_user_view, name="register"),
    path("me/", views.user_profile_view, name="profile"),
    path("me/points/", views.user_points_view, name="points"),
    path(
        "account/setup/verify/<str:uidb64>/<str:token>/",
        views.verify_account_setup_view,
        name="verify_setup_account",
    ),
    path("account/setup/", views.account_setup_view, name="setup_account"),
]
