from django.urls import path

from . import views

app_name = "users-auth"

urlpatterns = [
    # path(
    #     "login/",
    #     views.AuthLoginView.as_view(),
    #     name="login",
    # ),
    # path("logout/", views.AuthLogoutView.as_view(), name="logout"),
    path("resetpassword/", views.AuthPassResetView.as_view(), name="resetpassword"),
    path(
        "resetpassword/done/",
        views.AuthPassResetDoneView.as_view(),
        name="resetpassword_done",
    ),
    path(
        "resetpassword/complete/",
        views.AuthPassResetCompleteView.as_view(),
        name="resetpassword_complete",
    ),
    path(
        "resetpassword/<uidb64>/<token>/",
        views.AuthPassResetConfirmView.as_view(),
        name="resetpassword_confirm",
    ),
    path(
        "changepassword/",
        views.AuthChangePasswordView.as_view(),
        name="changepassword",
    ),
    path(
        "changepassword/done/",
        views.AuthPasswordChangeDoneView.as_view(),
        name="changepassword_done",
    ),
]
