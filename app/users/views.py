"""
HTML views.
"""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.http import HttpRequest
from django.shortcuts import redirect, render
from rest_framework.authtoken.models import Token

from clubs.models import ClubMembership
from users.services import UserService


@login_required()
def user_profile_view(request: HttpRequest):
    """Display user's profile."""
    user = request.user
    profile = user.profile

    club_memberships = ClubMembership.objects.filter(user=user).select_related("club")

    context = {
        "user": user,
        "profile": profile,
        "clubs": club_memberships,
    }

    return render(request, "users/profile.html", context=context)


@login_required()
def user_points_view(request: HttpRequest):
    """Summary showing the user's points."""
    return render(request, "users/points.html", context={})


def verify_account_setup_view(request: HttpRequest, uidb64: str, token: str):
    """
    Allow users to finish setting up their account.

    They get this link after their user has been created for the first
    time by an admin. The user doesn't have a password yet, and does
    not have any oauth connections - so they are manually authenticated
    via a "password reset token", so they can "change" (set) their password
    or connect any oauth accounts.
    """

    next = request.GET.get("next", None)

    try:
        user = UserService.verify_account_setup_token(uidb64, token)
        auth_token, _ = Token.objects.get_or_create(user=user)
    except Exception as e:
        if next:
            return redirect(next + f"?error={str(e)}")
        else:
            raise e

    login(request, user, backend="core.backend.CustomBackend")

    if next:
        return redirect(next + f"?token={auth_token}")

    # return redirect("users:setup_account")
    return redirect("users-auth:changepassword")


@login_required()
def account_setup_view(request: HttpRequest):
    """User must authenticate via link first."""

    form = SetPasswordForm(request.user)

    return render(
        request,
        "users/setup_account.html",
        context={"form": form, "user": request.user},
    )
