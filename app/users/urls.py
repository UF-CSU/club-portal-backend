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
]
