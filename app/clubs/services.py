import io
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from django.template.loader import render_to_string
from django.utils.html import strip_tags
import icalendar
from django.core import exceptions, mail
from django.db import models
from django.urls import reverse

from app.settings import DEFAULT_FROM_EMAIL
from clubs.models import (
    Club,
    ClubMembership,
    ClubRole,
    DayChoice,
    Event,
    EventAttendance,
    RecurringEvent,
)
from core.abstracts.services import ServiceBase
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

    def record_event_attendance(self, user: User, event: Event):
        """Record user's attendance for event."""

        # member = self._get_user_membership(user)
        member, _ = ClubMembership.objects.get_or_create(user=user, club=event.club)

        if event.club.id != self.obj.id:
            raise exceptions.BadRequest(
                f'Event "{event}" does not belong to club {self.obj}.'
            )

        attendence, _ = EventAttendance.objects.get_or_create(
            member=member, event=event
        )
        return attendence

    def get_member_attendance(self, user: User):
        """Get event attendance for user, if they are member."""

        member = self._get_user_membership(user)
        return EventAttendance.objects.filter(member=member)

    def create_event(
        self,
        name: str,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        recurring_event=None,
    ):
        """Create new club event."""
        if start_at and end_at and (start_at >= end_at):
            raise exceptions.BadRequest(
                "The event start time must be before the end time."
            )

        event = Event.objects.create(
            club=self.obj,
            name=name,
            start_at=start_at,
            end_at=end_at,
            recurring_event=recurring_event,
        )
        return event

    def create_recurring_event(
        self,
        name: str,
        start_date: datetime,
        end_date: datetime,
        day: DayChoice,
        event_start_time: time,
        event_end_time: time,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Create new recurring club event, trigger signal for syncing event."""

        return RecurringEvent.objects.create(
            name=name,
            club=self.obj,
            start_date=start_date,
            end_date=end_date,
            day=day,
            event_start_time=event_start_time,
            event_end_time=event_end_time,
            location=location,
            description=description,
        )

    def create_calendar(self, name: str):
        cal = icalendar.Calendar()
        cal.add("PRODID", "-//CSU Portal//UF CSU//EN")
        cal.add("VERSION", "2.0")
        cal.add("X-WR-CALNAME", name)
        # Suggest refresh interval of 1hr
        cal.add("X-PUBLISHED-TTL", "PT1H")
        return cal

    def create_calendar_event(self, event: Event, tz: ZoneInfo):
        e = icalendar.Event()
        e.add("SUMMARY", f"{event.name} | {event.club.name}")
        if event.description is not None:
            e.add("DESCRIPTION", event.description)
        if event.start_at is not None and event.end_at is not None:
            local_start_at = event.start_at.replace(tzinfo=tz)
            local_end_at = event.end_at.replace(tzinfo=tz)
            e.add("DTSTART", local_start_at)
            e.add("DTEND", local_end_at)
        if event.location is not None:
            e.add("LOCATION", event.location)
        return e

    def get_event_calendar(self, event: Event):
        """Generates an ICS file for an event."""
        if event.club.id != self.obj.id:
            raise exceptions.BadRequest(
                f'Event "{event}" does not belong to club {self.obj}.'
            )

        # Initialize calendar
        cal = self.create_calendar(f"{event.name} | {event.club.name}")
        cal.add("X-WR-CALDESC", event.description)

        # Configure timezone
        local_tz = ZoneInfo("America/New_York")

        # Create event
        e = self.create_calendar_event(event, local_tz)

        # Add recurring event
        if event.recurring_event is not None:
            days = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
            options = {
                "FREQ": "WEEKLY",
                "INTERVAL": 1,
                "BYDAY": days[event.recurring_event.day],
            }
            if event.recurring_event.end_date is not None:
                until = datetime.combine(
                    event.recurring_event.end_date, datetime.min.time()
                )
                aware_until = until.replace(tzinfo=local_tz)
                options["UNTIL"] = aware_until

            e.add("RRULE", options)

        cal.add_component(e)

        cal.add_missing_timezones()

        buffer = io.BytesIO(cal.to_ical())
        buffer.seek(0)
        return buffer

    def get_calendar(self):
        """Generates an ICS file for a club containing all future events."""
        # Initialize calendar
        cal = self.create_calendar(self.obj.name)
        cal.add("X-WR-CALDESC", f"Calendar for {self.obj.name}")

        # Configure timezone
        local_tz = ZoneInfo("America/New_York")

        # Get all events that start later than today
        now = datetime.now().replace(tzinfo=local_tz)
        query = Event.objects.filter(start_at__gt=now)

        for event in query:
            e = self.create_calendar_event(event, local_tz)
            cal.add_component(e)

        cal.add_missing_timezones()

        buffer = io.BytesIO(cal.to_ical())
        buffer.seek(0)
        return buffer

    def get_attendance_url(self, event: Event):
        """Visiting this link will register a user for an event."""

        return reverse("clubs:joinevent", event_id=event.id)

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

    @classmethod
    def sync_recurring_event(cls, rec_ev: RecurringEvent):
        """
        Sync all events for recurring event template.

        Will remove all excess events outside of start/end dates,
        and will create events if missing on a certain day.

        Date filter docs:
        https://docs.djangoproject.com/en/dev/ref/models/querysets/#week-day
        """
        event_count = rec_ev.expected_event_count + 2  # Buffer before/after

        # Remove extra events
        # Get all dates assigned to recurring,
        # delete if they don't overlap with the start/end dates
        range_start = datetime.combine(rec_ev.start_date, rec_ev.event_start_time)
        range_end = datetime.combine(rec_ev.end_date, rec_ev.event_start_time)

        # Django filter starts at Sun=1, python starts Mon=0
        query_day = rec_ev.day + 2 if rec_ev.day > 0 else 6

        query = rec_ev.events.filter(
            ~models.Q(start_at__date__range=(range_start, range_end))
            | ~models.Q(start_at__week_day=query_day)
        )
        query.delete()

        # Create missing events
        for i in range(event_count):
            # Equalize date to monday (0), set to target day, set to target week (i)
            event_date = (
                (rec_ev.start_date - timedelta(days=rec_ev.start_date.weekday()))
                + timedelta(days=rec_ev.day)
                + timedelta(weeks=i)
            )

            if event_date < rec_ev.start_date or event_date > rec_ev.end_date:
                continue

            event_start = datetime.combine(
                event_date, rec_ev.event_start_time, tzinfo=timezone.utc
            )
            event_end = datetime.combine(
                event_date, rec_ev.event_end_time, tzinfo=timezone.utc
            )

            # These fields must all be unique together
            event, _ = Event.objects.update_or_create(
                name=rec_ev.name,
                club=rec_ev.club,
                start_at=event_start,
                end_at=event_end,
                recurring_event=rec_ev,
            )

            # Set other fields
            event.location = rec_ev.location

            # Only add description if not exists
            # Doesn't override custom description for existing events
            if event.description is None:
                event.description = rec_ev.description

            event.save()
