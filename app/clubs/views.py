"""
Club views for API and rendering html pages.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

#from asgiref import sync_to_async

from clubs.forms import AdminInviteForm
from clubs.models import Club, RoleType
from clubs.services import ClubService
from users.models import User, UserManager
from users.services import UserService
from utils.admin import get_admin_context


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
        form = AdminInviteForm(request.POST)
        if form.is_valid():
            data = request.POST

            print(data)

            email = data["email"]
            user = None
            created = False
            try:
                user = get_object_or_404(User, email=email)
            except:

                print("No user")

                user = User.objects.create_user(email)
                created = True
                #if not create user

            print(user)


            club_id = data["club"]
            club = Club.objects.get(pk=club_id)

            print(club)

            # Get list of club roles, and pick an admin role
            admin_roles = club.roles.filter(role_type=RoleType.ADMIN).exclude(name__iexact="President")
            print(admin_roles)
            assigned_role = [admin_roles.first()]
            print(assigned_role)

            #check if they are a member
            #try:
            #    membership = ClubService(club)._get_user_membership(user)
            #    
            #except:
            #    print()

            #Email that they joined the club


            send_inv = data["send_inv"]
            print(send_inv)
            #Email for account set up if needed

            ClubService(club).add_member(user, assigned_role, send_email=send_inv)

            #Email for account set up if needed
            UserService(user).send_account_setup_link()

    else:
        form = AdminInviteForm()

    context["form"] = form

    return render(request, "admin/clubs/invite_club_admin.html", context=context)