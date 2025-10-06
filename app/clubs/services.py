from typing import Optional

from django.core import exceptions
from django.urls import reverse

from clubs.models import Club, ClubMembership, ClubRole
from core.abstracts.services import ServiceBase
from events.models import EventAttendance
from lib.emails import send_html_mail
from users.models import User
from utils.helpers import get_full_url


class ClubService(ServiceBase[Club]):
    """Manage club objects, business logic."""

    model = Club

    def _get_user_membership(self, user: User):
        try:
            return ClubMembership.objects.get(club=self.obj, user=user)
        except ClubMembership.DoesNotExist as e:
            raise exceptions.BadRequest(f"User is not a member of {self.obj}.") from e

    @property
    def join_url(self):
        """Get url path for a new user to create account and register."""

        return reverse("clubs:join", kwargs={"club_id": self.obj.id})

    @property
    def full_join_url(self):
        """Gives the full url with protocol, FQDN, and path for joining club."""

        return get_full_url(self.join_url)

    @property
    def logo_url(self) -> str:
        """Get the logo URL for the club."""
        if self.obj.logo:
            return self.obj.logo.url
        return ""

    def add_member(
        self,
        user: User,
        roles: Optional[list[ClubRole | str]] = None,
        send_email=False,
        club_redirect_url=None,
        fail_silently=True,
        **kwargs,
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
        member = ClubMembership.objects.create(
            club=self.obj, user=user, roles=roles, **kwargs
        )
        url = club_redirect_url or get_full_url(reverse("clubs:home", args=[user.id]))

        if send_email:
            send_html_mail(
                subject=f"You have been added to as a member of {self.obj.name}",
                to=[user.email],
                html_template="clubs/email_invite_template.html",
                html_context={"invite_url": url},
            )

        return member

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
        member.save()

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
        """Send email invite to list of emails separately."""

        send_html_mail(
            subject=f"You have been invited to {self.obj.name}",
            to=emails,
            html_template="clubs/email_invite_template.html",
            html_context={
                "club_name": self.obj.name,
                "invite_url": self.full_join_url,
                "logo_url": self.logo_url,
            },
            send_separately=True,
        )
