from typing import Optional

from app.settings import CLUB_INVITE_REDIRECT_URL
from core.abstracts.services import ServiceBase
from django.core import exceptions
from django.db import transaction
from django.urls import reverse
from events.models import EventAttendance
from lib.emails import send_html_mail
from users.models import User
from users.services import UserService
from utils.helpers import get_full_url

from clubs.models import Club, ClubMembership, ClubRole


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

    def _parse_club_role(self, role: ClubRole | str) -> ClubRole:
        """Validate role exists in club."""

        if isinstance(role, str):
            role = self.obj.roles.get(name=role)

        if role.club.id != self.obj.id:
            raise exceptions.BadRequest(
                f"Role {role.name} ({role.pk}) is not a part of club {self.obj.name}"
            )

        return role

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
        url = club_redirect_url or CLUB_INVITE_REDIRECT_URL % {"id": self.obj.id}

        if send_email:
            send_html_mail(
                subject=f"You have been added to the club {self.obj.name}",
                to=[user.email],
                html_template="clubs/email_invite_template.html",
                html_context={"invite_url": url},
            )

        return member

    def set_member_role(self, user: User, role: ClubRole | str):
        """Replace a member's roles with given role."""

        if role:
            role = self._parse_club_role(role)

        member = self._get_user_membership(user)
        member.roles.clear()
        member.add_roles(role)

    def add_member_role(self, user: User, role: ClubRole | str):
        """Add role to member's roles."""

        if role:
            role = self._parse_club_role(role)

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

    def invite_user_to_club(
        self,
        email: str,
        is_owner=False,
        send_email_invite=True,
        force_send_account_link=False,
        role: Optional[ClubRole | str] = None,
    ) -> tuple[ClubMembership, bool]:
        """Get/create user for email and add them to club."""

        with transaction.atomic():
            # Parse role if necessary
            if role is not None:
                role = self._parse_club_role(role)

            # Get or create new user
            user = User.objects.find_by_email(email)
            user_created = False

            if not user:
                # Send account setup link if being created
                user = User.objects.create_user(email)
                user_created = True

            if user_created or force_send_account_link:
                UserService(user).send_account_setup_link()

            # Raise error if user is in club already
            if self.obj.memberships.filter(user__id=user.id).exists():
                raise exceptions.ValidationError(
                    f'User is already member of club "{self.obj.name}"'
                )

            return self.add_member(
                user,
                send_email=send_email_invite,
                is_owner=is_owner,
                fail_silently=False,
                roles=[role] if role is not None else None,
            ), user_created
