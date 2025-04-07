"""
Club views for API and rendering html pages.
"""

from clubs.models import Club
from clubs.services import ClubService
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from users.models import User


@login_required()
def join_club_view(request: HttpRequest, club_id: int):
    """Registers a new or existing user to a club."""
    club = get_object_or_404(Club, id=club_id)

    club_svc = ClubService(club)
    club_svc.add_member(request.user)

    url = reverse("clubs:home", kwargs={"club_id": club.id})
    return redirect(url)


def club_home_view(request: HttpRequest, club_id: int):
    """Base page for a club."""
    club = get_object_or_404(Club, id=club_id)

    return render(request, "clubs/club_home.html", context={"club": club})


@login_required()
def available_clubs_view(request: HttpRequest):
    """Display list of clubs to user for them to join."""

    return render(request, "clubs/available_clubs.html")


def accept_invite(request: HttpRequest, user_id: int):
    """Accept invite to club."""

    user = get_object_or_404(User, id=user_id)
    login(request, user, backend="core.backend.CustomBackend")

    if user.can_authenticate:
        return JsonResponse({"message": "This should redirect to client..."})
    else:
        return redirect("users:setupaccount", args=[user_id])


# def setup_account(request: HttpRequest, user_id: int):
#     """If user is inactive, direct them to oauth, otherwise redirect them to final url."""

#     print("user is active:", user.is_active)

#     # FIXME: Check for valid token, just userid is huge security flaw

#     if user.is_active:
#         return JsonResponse({"message": f"Accepted for user {user.email}"})
#     else:
#         # request.session = {}
#         user.is_active = True
#         user.save()
#         login(request, user, backend="core.backend.CustomBackend")

#         return redirect("account_change_password")
