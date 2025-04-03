"""
HTML views.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import BadRequest, ValidationError
from django.http import HttpRequest
from django.shortcuts import redirect, render
from rest_framework import status

from clubs.models import Club, ClubMembership
from clubs.services import ClubService
from events.models import Event
from events.services import EventService
from users.forms import RegisterForm
from users.services import UserService


def register_user_view(request: HttpRequest):
    """Add new user to the system."""

    if request.user.is_authenticated:
        print("User logged in!")
        return redirect("/")

    context = {}
    initial_data = {}

    if request.POST:
        form = RegisterForm(data=request.POST)

        if form.is_valid():
            data = form.cleaned_data
            form_data = {
                "first_name": data.get("first_name", None),
                "last_name": data.get("last_name", None),
                "email": data.get("email", None),
                "password": data.get("password", None),
            }

            confirmed_password = data.get("confirm_password", None)

            if confirmed_password != form_data["password"]:
                raise ValidationError("Passwords do not match.")

            user = UserService.register_user(**form_data)
            UserService.login_user(request, user)

            club: Club = data.get("club", None)
            event: Event = data.get("event", None)

            if club:
                ClubService(club).add_member(user)

            if event:
                ClubService(event.club).add_member(user)
                EventService(event).record_event_attendance(user)

            if "next" in request.GET:
                return redirect(request.GET.get("next"))
            else:
                return redirect("clubs:available")

        else:
            context["form"] = form
            return render(
                request,
                "users/register_user.html",
                context,
                status=status.HTTP_400_BAD_REQUEST,
            )

    elif request.method == "GET":
        club_id = request.GET.get("club", None)
        event_id = request.GET.get("event", None)

        if club_id:
            initial_data["club"] = Club.objects.find_by_id(int(club_id))

        if event_id:
            initial_data["event"] = Event.objects.find_by_id(int(event_id))

        form = RegisterForm(initial=initial_data)

    else:
        raise BadRequest("Method must be GET or POST.")

    context["form"] = form
    return render(request, "users/register_user.html", context)


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
