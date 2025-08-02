import datetime
import io
from zoneinfo import ZoneInfo

import icalendar
from django.db import models
from django.urls import reverse
from django.utils import timezone

from clubs.models import Club
from core.abstracts.schedules import schedule_clocked_func
from core.abstracts.services import ServiceBase
from events.models import Event, EventAttendanceLink, RecurringEvent
from utils.dates import get_day_count
from utils.helpers import get_full_url


class RecurringEventService(ServiceBase[RecurringEvent]):
    """Business logic for Recurring Events."""

    model = RecurringEvent

    def sync_events(self):
        """
        Sync all events for recurring event template.

        Will remove all excess events outside of start/end dates,
        and will create events if missing on a certain day.

        Returns a queryset of all events for a recurring event.

        Date filter docs:
        https://docs.djangoproject.com/en/dev/ref/models/querysets/#week-day
        """
        self.obj.refresh_from_db()
        rec_ev = self.obj

        # Remove extra events
        # Get all dates assigned to recurring,
        # delete if they don't overlap with the start/end dates
        range_start = datetime.datetime.combine(
            rec_ev.start_date, rec_ev.event_start_time
        )
        range_end = datetime.datetime.combine(rec_ev.end_date, rec_ev.event_start_time)

        # Django filter starts at Sun=1, python starts Mon=0
        query_days = [day + 2 if day > 0 else 6 for day in rec_ev.days]

        # Delete events outside of range
        query = rec_ev.events.filter(
            ~models.Q(start_at__date__range=(range_start, range_end))
            | ~models.Q(start_at__week_day__in=query_days)
        )
        query.delete()

        # Sync events for each day
        start = rec_ev.start_date
        end = rec_ev.end_date

        for day in rec_ev.days:
            # Buffer in first and last date
            for i in range(get_day_count(start, end, day) + 2):

                # Calculate event date using timedelta from index
                event_date = (
                    (start - datetime.timedelta(days=start.weekday()))
                    + datetime.timedelta(days=day)
                    + datetime.timedelta(weeks=i)
                )

                if event_date < start or event_date > end:
                    continue

                event_start = datetime.datetime.combine(
                    event_date, rec_ev.event_start_time, tzinfo=timezone.utc
                )

                if rec_ev.event_start_time > rec_ev.event_end_time:
                    event_date += datetime.timedelta(days=1)

                event_end = datetime.datetime.combine(
                    event_date, rec_ev.event_end_time, tzinfo=timezone.utc
                )

                # These fields must all be unique together
                event, _ = Event.objects.update_or_create(
                    name=rec_ev.name,
                    start_at=event_start,
                    end_at=event_end,
                    recurring_event=rec_ev,
                    defaults=rec_ev.get_event_update_kwargs(),
                )

                # Sync hosts
                if rec_ev.club:
                    event.add_host(rec_ev.club, is_primary=True)

                if rec_ev.other_clubs.all().count() > 0:
                    event.add_hosts(*rec_ev.other_clubs.all())

                # Sync attachments
                # TODO: Should admins be allowed to set custom attachments for individual events?
                rec_ev.refresh_from_db()
                event.attachments.set(rec_ev.attachments.all())

                event.save()

        rec_ev.last_synced = timezone.now()
        rec_ev.save()

        return rec_ev.events.all()


class EventService(ServiceBase[Event]):
    """Business logic for Events."""

    model = Event

    @property
    def attendance_url(self):
        return reverse("api-events:attendance-list", args=[self.obj.id])

    @property
    def full_attendance_url(self):
        return get_full_url(self.attendance_url)

    def create_attendance_link(self, club: Club, generate_qrcode=True, **kwargs):
        """
        Create an event attendance link for a club.

        Optionally add additional kwargs to model during creation.
        """

        link = EventAttendanceLink.objects.create(
            url=self.full_attendance_url,
            event=self.obj,
            club=club,
            **kwargs,
        )

        if generate_qrcode:
            link.generate_qrcode()

        return link

    def sync_hosts_attendance_links(self):
        """For each club hosting the event, make sure they have at least one attendance link."""

        for club in self.obj.clubs.all():
            if EventAttendanceLink.objects.filter(event=self.obj, club=club).exists():
                continue

            self.create_attendance_link(club)

    @staticmethod
    def create_calendar(name: str):
        cal = icalendar.Calendar()
        cal.add("PRODID", "-//CSU Portal//UF CSU//EN")
        cal.add("VERSION", "2.0")
        cal.add("X-WR-CALNAME", name)
        # Suggest refresh interval of 1hr
        cal.add("X-PUBLISHED-TTL", "PT1H")
        return cal

    def create_calendar_event(self, tz: ZoneInfo):
        event = self.obj

        e = icalendar.Event()
        e.add("SUMMARY", f"{event.name} | {event.primary_club.name}")
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

    def get_event_calendar(self):
        """Generates an ICS file for an event."""
        event = self.obj

        # Initialize calendar
        cal = self.create_calendar(f"{event.name} | {event.primary_club.name}")
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
                until = datetime.datetime.combine(
                    event.recurring_event.end_date, datetime.datetime.min.time()
                )
                aware_until = until.replace(tzinfo=local_tz)
                options["UNTIL"] = aware_until

            e.add("RRULE", options)

        cal.add_component(e)

        cal.add_missing_timezones()

        buffer = io.BytesIO(cal.to_ical())
        buffer.seek(0)
        return buffer

    @classmethod
    def get_club_calendar(cls, club: Club):
        """Generates an ICS file for a club containing all future events."""
        # Initialize calendar
        cal = cls.create_calendar(club.name)
        cal.add("X-WR-CALDESC", f"Calendar for {club.name}")

        # Configure timezone
        local_tz = ZoneInfo("America/New_York")

        # Get all events that start later than today
        now = datetime.datetime.now().replace(tzinfo=local_tz)
        query = Event.objects.filter(start_at__gt=now)

        for event in query:
            e = cls(event).create_calendar_event(event, local_tz)
            cal.add_component(e)

        cal.add_missing_timezones()

        buffer = io.BytesIO(cal.to_ical())
        buffer.seek(0)
        return buffer

    def schedule_make_public_task(self):
        """Create new periodic task to set event to public."""

        task = schedule_clocked_func(
            name=f"Make {self.obj.name} public",
            due_at=self.obj.make_public_at,
            func=make_event_public,
            kwargs={"event_id": self.obj.pk},
        )

        self.obj.make_public_task = task
        self.obj.save()

        return task


def make_event_public(event_id: int):
    """Function called when making an event public."""
    event = Event.objects.get(id=event_id)

    event.is_public = True
    event.save()
