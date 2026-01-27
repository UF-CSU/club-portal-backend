"""
Club views for API and rendering html pages.
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core import exceptions
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from utils.admin import get_admin_context

# from asgiref import sync_to_async
from clubs.forms import AdminInviteForm
from clubs.models import Club
from clubs.services import ClubService


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


@staff_member_required
@login_required
def invite_club_admin_view(request):
    context = get_admin_context(request)

    form = AdminInviteForm()

    if request.method == "POST":
        form = AdminInviteForm(data=request.POST)
        if form.is_valid():
            club = form.cleaned_data.get("club")
            email = form.cleaned_data.get("email")
            is_owner = form.cleaned_data.get("is_owner")
            send_invite = form.cleaned_data.get("send_invite")

            try:
                member, created = ClubService(club).invite_user_to_club(
                    email=email, is_owner=is_owner, send_email_invite=send_invite
                )

                # Reset form
                form = AdminInviteForm()

                # Show success message to admin
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "%s user %s successfully added to club %s as %s and %s"
                    % (
                        "New (account setup link sent)" if created else "Existing",
                        member.user.email,
                        member.club.name,
                        "owner" if is_owner else "non-owner",
                        "sent club email invite"
                        if send_invite
                        else "not sent club email invite",
                    ),
                )

            except exceptions.ValidationError as e:
                form.add_error(field=None, error=e)

    else:
        form = AdminInviteForm()

    context["form"] = form
    return render(request, "admin/clubs/invite_club_admin.html", context=context)
