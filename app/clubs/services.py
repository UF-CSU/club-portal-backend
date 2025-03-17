from typing import Optional

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core import exceptions, mail
from django.urls import reverse

from app.settings import DEFAULT_FROM_EMAIL
from clubs.models import (
    Club,
    ClubMembership,
    ClubRole,
)
from core.abstracts.services import ServiceBase
from events.models import EventAttendance
from users.models import User
from utils.helpers import get_full_url


class ClubService(ServiceBase[Club]):
    """Manage club objects, business logic."""

    model = Club

    def _get_user_membership(self, user: User):
        try:
            return ClubMembership.objects.get(club=self.obj, user=user)
        except ClubMembership.DoesNotExist:
            raise exceptions.BadRequest(f"User is not a member of {self.obj}.")

    @property
    def join_url(self):
        """Get url path for a new user to create account and register."""

        return reverse("clubs:join", kwargs={"club_id": self.obj.id})

    @property
    def full_join_url(self):
        """Gives the full url with protocol, FQDN, and path for joining club."""

        return get_full_url(self.join_url)

    def add_member(
        self, user: User, roles: Optional[list[ClubRole]] = None, fail_silently=True
    ):
        """Create membership for pre-existing user."""

        # If membership exists, just sync roles and continue
        member_query = ClubMembership.objects.filter(club=self.obj, user=user)
        if fail_silently and member_query.exists():
            if not roles:
                return

            member = member_query.first()
            member.add_roles(*roles)

            return

        # Create new membership
        return ClubMembership.objects.create(club=self.obj, user=user, roles=roles)

    def set_member_role(self, user: User, role: ClubRole | str):
        """Replace a member's roles with given role."""

        if isinstance(role, str):
            role = self.obj.roles.get(name=role)

        member = self._get_user_membership(user)
        member.roles.clear()
        member.add_roles(role)

    def add_member_role(self, user: User, role: ClubRole | str):
        """Add role to member's roles."""

        if isinstance(role, str):
            role = self.obj.roles.get(name=role)

        member = self._get_user_membership(user)
        member.add_roles(role)

    def increase_member_points(self, user: User, amount: int = 1):
        """Give the user more coins."""
        member = self._get_user_membership(user)
        member.points += amount
        member.save()

    def decrease_member_points(self, user: User, amount: int = 1):
        """Remove coins from the user."""
        member = self._get_user_membership(user)
        if member.points < amount:
            raise exceptions.BadRequest("Not enough coins to decrease.")
        else:
            member.points -= amount

        member.save()

    def get_member_event_attendance(self, user: User):
        """Get event attendance for user, if they are member."""

        member = self._get_user_membership(user)
        return EventAttendance.objects.filter(member=member)

    def send_email_invite(self, emails: list[str]):
        """Send email invite to list of emails."""

        html_body = render_to_string(
            "clubs/email_invite_template.html",
            context={"invite_url": self.full_join_url},
        )
        text_body = strip_tags(html_body)

        for email in emails:
            message = mail.EmailMultiAlternatives(
                from_email=DEFAULT_FROM_EMAIL,
                subject=f"You have been invited to {self.obj.name}",
                body=text_body,
                to=[email],
            )
            message.attach_alternative(html_body, "text/html")
            message.send()
