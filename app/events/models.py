"""
Event models.
"""

from datetime import date, time
from typing import ClassVar, Optional

from django.db import models
from django.utils import timezone
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from analytics.models import Link
from clubs.models import Club
from core.abstracts.models import ManagerBase, ModelBase, Scope, Tag
from users.models import User
from utils.dates import get_day_count


class DayChoice(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class EventType(models.TextChoices):
    """Broad type of event."""

    GBM = "gbm", _("GBM")
    WORKSHOP = "workshop", _("Workshop")
    SOCIAL = "social", _("Social")
    INTERNAL_MEETING = "internal_meeting", _("Internal Meeting")
    SPEAKER = "speaker", _("Speaker")
    OTHER = "other", _("Other")


class EventTag(Tag):
    """Group together different types of events."""


class EventFields(ModelBase):
    """Common fields for club event models."""

    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    event_type = models.CharField(choices=EventType.choices, default=EventType.OTHER)

    location = models.CharField(null=True, blank=True, max_length=255)

    class Meta:
        abstract = True


class RecurringEventManager(ManagerBase["RecurringEvent"]):
    """Manage queries for RecurringEvents."""

    def create(
        self,
        name: str,
        day: DayChoice,
        start_date: date,
        end_date: Optional[date] = None,
        club: Optional[Club] = None,
        other_clubs: Optional[list[Club]] = None,
        **kwargs,
    ):
        rec_ev = super().create(
            name=name,
            day=day,
            start_date=start_date,
            end_date=end_date,
            club=club,
            **kwargs,
        )

        if other_clubs:
            rec_ev.other_clubs.set(other_clubs)
            rec_ev.save()

        return rec_ev


def get_default_start_time():
    """Returns default start time to use if not provided for event models."""
    return time(0, 0, 0)


def get_default_end_time():
    """Returns default end time to use if not provided for event models."""
    return time(23, 59, 59)


class RecurringEvent(EventFields):
    """Template for recurring events."""

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="recurring_events",
        help_text="Club that owns recurring template, hosts all the events from it.",
        null=True,
        blank=True,
    )

    day = models.IntegerField(choices=DayChoice.choices)
    event_start_time = models.TimeField(
        blank=True,
        help_text="Each event will start at this time",
        default=get_default_start_time,
    )
    event_end_time = models.TimeField(
        blank=True,
        help_text="Each event will end at this time",
        default=get_default_end_time,
    )

    start_date = models.DateField(help_text="Date of the first occurance of this event")
    end_date = models.DateField(
        null=True, blank=True, help_text="Date of the last occurance of this event"
    )
    # TODO: add skip_dates field

    other_clubs = models.ManyToManyField(
        Club, blank=True, help_text="These clubs host the events as secondary hosts."
    )

    # Relationships
    events: models.QuerySet["Event"]

    # Dynamic properties & methods
    @property
    def expected_event_count(self):
        # TODO: How to handle no end date?
        if self.end_date is None:
            end_date = timezone.now()
        else:
            end_date = self.end_date

        return get_day_count(self.start_date, end_date, self.day)

    @property
    def all_day(self):
        return (
            self.event_start_time == get_default_start_time()
            and self.event_end_time == get_default_end_time()
        )

    # Overrides
    objects: ClassVar[RecurringEventManager] = RecurringEventManager()


class EventManager(ManagerBase["Event"]):
    """Manage event queries."""

    def create(
        self,
        name: str,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        host: Optional[Club] = None,
        secondary_hosts: Optional[list[Club]] = None,
        **kwargs,
    ):
        """Create new event, and attendance link."""

        event = super().create(name=name, start_at=start_at, end_at=end_at, **kwargs)

        if host:
            event.add_host(host, is_primary=True)
        if secondary_hosts:
            event.add_hosts(*secondary_hosts)

        return event


class Event(EventFields):
    """
    Record general and club events.

    DateTimeRange docs:
    https://docs.djangoproject.com/en/5.1/ref/contrib/postgres/fields/#datetimerangefield
    """

    scope = Scope.CLUB

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(default=timezone.now)

    recurring_event = models.ForeignKey(
        RecurringEvent,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
    )

    tags = models.ManyToManyField(EventTag, blank=True)

    # Foreign Relationships
    clubs = models.ManyToManyField(Club, through="events.EventHost", blank=True)
    attendance_links: models.QuerySet["EventAttendanceLink"]
    hosts: models.QuerySet["EventHost"]

    @property
    def primary_club(self):
        """Get the primary club hosting the event."""

        host = self.hosts.filter(is_primary=True)
        if not host.exists():
            return None

        return host.first().club

    @property
    def club(self):
        return self.primary_club

    @property
    def all_day(self) -> bool:
        return (
            self.start_at.time() == get_default_start_time()
            and self.end_at.time() == get_default_end_time()
        )

    @property
    def is_cancelled(self):
        return hasattr(self, "cancellation")

    # Overrides
    objects: ClassVar[EventManager] = EventManager()

    def __str__(self) -> str:
        if self.start_at:
            return super().__str__() + f' ({self.start_at.strftime("%a %m/%d")})'

        return super().__str__()

    # Methods
    def add_host(self, club: Club, is_primary=False, commit=True):
        """
        Add a new club host to an event.

        If commit=True, this method will call ``save()`` on the event to trigger
        ``post_save`` actions with the newly added hosts.
        """

        host, _ = EventHost.objects.get_or_create(event=self, club=club)

        # Only update if the default arg is overwritten
        if is_primary is True:
            # TODO: Remove current primary host
            host.is_primary = True
            host.save()

        if commit:
            self.save()  # Rerun post_save actions for event

        return host

    def add_hosts(self, *clubs: list[Club]):
        """Add list of hosts to event."""

        for club in clubs:
            self.add_host(club)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_event_by_name_and_time",
                fields=["name", "start_at", "end_at"],
            )
        ]


class EventHost(ModelBase):
    """Attach clubs to events."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="hosts")
    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="event_hostings"
    )
    is_primary = models.BooleanField(
        default=False,
        blank=True,
        help_text="This is the main club that hosts the event.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="one_primary_host_per_event",
                fields=("event", "is_primary"),
                condition=models.Q(is_primary=True),
            )
        ]


class EventAttendance(ModelBase):
    """
    Records when user attend an event.

    It is scoped to the user level and not clubmember level
    to allow tracking of users for non-club events.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="user_attendance",
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="event_attendance"
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=("event", "user"),
                name="record_attendance_once_per_user_per_event",
            )
        ]


class EventAttendanceLinkManager(ManagerBase["EventAttendanceLink"]):
    """Manage queries for event links."""

    def create(self, url: str, event: Event, club, **kwargs):
        """Create event attendance link."""

        assert club in event.clubs.all(), f"{club} is not a host of {event}"

        payload = {
            "target_url": url,
            "event": event,
            "display_name": kwargs.pop("display_name", f"Join {event.__str__()} Link"),
            "club": club,
            **kwargs,
        }

        return super().create(**payload)


class EventAttendanceLink(Link):
    """
    Manage links for event attendance.

    Extends Link model via one-to-one relationship, sharing a pk.
    All fields from link are accessible on this model.
    The display name is used for seeing the value of the link in a table view,
    and the reference is used as a unique key to use in tracking.
    """

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="attendance_links"
    )
    reference = models.CharField(
        null=True, blank=True, help_text="Used to differentiate between links"
    )

    # Overrides
    objects: ClassVar["EventAttendanceLinkManager"] = EventAttendanceLinkManager()

    def __str__(self):
        if self.reference:
            return f"{super().__str__()} ({self.reference})"
        else:
            return super().__str__()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("event", "reference"),
                name="unique_reference_per_event_attendance_link",
            )
        ]


class EventCancellation(ModelBase):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="cancellation"
    )
    reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)
