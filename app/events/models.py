"""
Event models.
"""

from datetime import date, time
from typing import ClassVar, Optional
from zoneinfo import ZoneInfo

from django.core import exceptions
from django.db import models
from django.utils import timezone
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask

from analytics.models import Link
from clubs.models import Club, ClubFile, ClubScopedModel
from core.abstracts.models import ManagerBase, ModelBase, Tag
from users.models import User
from utils.dates import get_day_count
from utils.formatting import format_timedelta
from utils.models import ArrayChoiceField


class DayType(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")

    def to_query_weekday(self):
        """
        Convert number from day type to number used for django lookups.

        Mapping:
        Day       => S M T W R F S
        DayChoice => 6 0 1 2 3 4 5
        Django    => 1 2 3 4 5 6 7

        Ref: https://docs.djangoproject.com/en/dev/ref/models/querysets/#week-day
        """

        match self.value:
            case DayType.MONDAY:
                return 2
            case DayType.TUESDAY:
                return 3
            case DayType.WEDNESDAY:
                return 4
            case DayType.THURSDAY:
                return 5
            case DayType.FRIDAY:
                return 6
            case DayType.SATURDAY:
                return 7
            case DayType.SUNDAY:
                return 1
            case _:
                raise ValueError(f"Invalid day type: {self.value}")


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


class EventFields(ClubScopedModel, ModelBase):
    """Common fields for club event models."""

    name = models.CharField(max_length=128)
    event_type = models.CharField(
        choices=EventType.choices, default=EventType.OTHER, blank=True
    )
    description = models.TextField(null=True, blank=True)
    location = models.CharField(null=True, blank=True, max_length=255)

    attachments = models.ManyToManyField(
        ClubFile, blank=True, related_name="%(class)ss"
    )
    enable_attendance = models.BooleanField(
        default=False, help_text="Create poll for event and users to attend."
    )

    class Meta:
        abstract = True


class RecurringEventManager(ManagerBase["RecurringEvent"]):
    """Manage queries for RecurringEvents."""

    def create(
        self,
        name: str,
        days: list[DayType],
        start_date: date,
        end_date: date,
        club: Optional[Club] = None,
        **kwargs,
    ):
        attachments = kwargs.pop("attachments", [])
        other_clubs = kwargs.pop("other_clubs", [])

        rec_ev = super().create(
            name=name,
            days=days,
            start_date=start_date,
            end_date=end_date,
            club=club,
            **kwargs,
        )

        rec_ev.other_clubs.set(other_clubs)
        rec_ev.attachments.set(attachments)

        # Update events since already created from signal
        for event in rec_ev.events.all():
            event.attachments.set(attachments)
            event.clubs.add(*[club.id for club in list(other_clubs)])

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

    days = ArrayChoiceField(models.IntegerField(choices=DayType.choices))
    event_start_time = models.TimeField(
        blank=True,
        help_text="Each event will start at this time, in UTC",
        default=get_default_start_time,
    )
    event_end_time = models.TimeField(
        blank=True,
        help_text="Each event will end at this time, in UTC",
        default=get_default_end_time,
    )

    start_date = models.DateField(help_text="Date of the first occurance of this event")
    # TODO: Allow no end date
    end_date = models.DateField(help_text="Date of the last occurance of this event")
    is_public = models.BooleanField(default=True, blank=True)
    prevent_sync_past_events = models.BooleanField(
        blank=True,
        default=False,
        help_text="When syncing events, should past events be prevented from updating?",
    )

    # TODO: add skip_dates field

    other_clubs = models.ManyToManyField(
        Club, blank=True, help_text="These clubs host the events as secondary hosts."
    )

    last_synced = models.DateTimeField(
        null=True, blank=True, editable=False, help_text="Last time events were synced"
    )

    # Relationships
    events: models.QuerySet["Event"]

    # Dynamic properties & methods
    @property
    def expected_event_count(self):
        return sum(
            [get_day_count(self.start_date, self.end_date, day) for day in self.days]
        )

    @property
    def is_all_day(self) -> bool:
        return (
            self.event_start_time == get_default_start_time()
            and self.event_end_time == get_default_end_time()
        )

    @property
    def clubs(self):
        return Club.objects.filter(
            models.Q(id=self.club.id)
            | models.Q(id__id=list(self.other_clubs.all().values_list("id", flat=True)))
        )

    # Overrides
    objects: ClassVar[RecurringEventManager] = RecurringEventManager()

    def get_event_update_kwargs(self):
        """Get fields/values to update each event with."""

        return {
            "location": self.location,
            "event_type": self.event_type,
            "is_public": self.is_public,
            "description": self.description,
            "enable_attendance": self.enable_attendance,
        }


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

    def for_club(self, club: Club | int) -> models.QuerySet["Event"]:
        """Get events where the club is a host."""

        return Event.objects.filter(clubs__id=club.id)

    def filter_for_day(self, day: DayType | int):
        """Get events that match a day choice."""

        day_value = DayType(day).to_query_weekday()
        return self.filter(start_at__week_day=day_value)


class Event(EventFields):
    """
    Record general and club events.

    DateTimeRange docs:
    https://docs.djangoproject.com/en/5.1/ref/contrib/postgres/fields/#datetimerangefield
    """

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

    is_draft = models.BooleanField(default=False, db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)
    make_public_at = models.DateTimeField(null=True, blank=True)
    make_public_task = models.ForeignKey(
        PeriodicTask, null=True, blank=True, editable=False, on_delete=models.SET_NULL
    )

    # is_poll_submission_required = models.BooleanField(default=True)

    # Foreign Relationships
    clubs = models.ManyToManyField(
        Club, through="events.EventHost", blank=True, db_index=True
    )
    attendance_links: models.QuerySet["EventAttendanceLink"]
    hosts: models.QuerySet["EventHost"]
    attendances: models.QuerySet["EventAttendance"]

    @property
    def primary_club(self):
        """Get the primary club hosting the event."""

        host = self.hosts.filter(is_primary=True)
        if not host.exists():
            return None

        return host.first().club

    @property
    def poll(self):
        if not hasattr(self, "_poll"):
            return None
        return self._poll

    @poll.setter
    def poll(self, value):
        value.event = self
        value.save()

    @property
    def submissions(self):
        if not self.poll:
            return None
        return self.poll.submissions.all()

    @property
    def is_all_day(self) -> bool:
        LOCAL_TZ = ZoneInfo("America/New_York")
        return (
            self.start_at.astimezone(LOCAL_TZ).time() == get_default_start_time()
            and self.end_at.astimezone(LOCAL_TZ).time() == get_default_end_time()
        )

    @property
    def is_cancelled(self):
        return hasattr(self, "cancellation")

    @property
    def status(self):
        if timezone.now() < self.start_at:
            return "SCHEDULED"
        elif self.start_at <= timezone.now() < self.end_at:
            return "IN_PROGRESS"
        else:
            return "ENDED"

    @property
    def duration(self):
        return self.end_at - self.start_at

    @property
    def duration_display(self):
        format_timedelta(self.duration)

    # Overrides
    objects: ClassVar[EventManager] = EventManager()

    def __str__(self) -> str:
        if self.start_at:
            return super().__str__() + f" ({self.start_at.strftime('%a %m/%d')})"

        return super().__str__()

    def clean(self, *args, **kwargs):
        if self.start_at > self.end_at:
            raise exceptions.ValidationError(
                "Start date cannot be greater than end date"
            )

        # If creating event, ensure no name clashes
        if self.pk is None and Event.objects.filter(
            name=self.name, start_at=self.start_at, end_at=self.end_at
        ):
            # Account for multiple duplicate events
            index = 1
            while Event.objects.filter(
                name=f"{self.name} {index}", start_at=self.start_at, end_at=self.end_at
            ).exists():
                index += 1

            self.name = f"{self.name} {index}"

        # # Constraint: if poll is None, is_poll_submission_required must be False
        # # NOTE: This is not a regular Constraint since poll is a virtual property
        # if not self.poll and self.is_poll_submission_required:
        #     self.is_poll_submission_required = False

        if self.pk and self.enable_attendance is True and self.primary_club is None:
            raise exceptions.ValidationError(
                "Cannot measure attendance without a primary host club."
            )

        return super().clean(*args, **kwargs)

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
        permissions = [("view_private_event", "Can view private event")]
        constraints = [
            models.UniqueConstraint(
                name="unique_event_by_name_and_time",
                fields=["name", "start_at", "end_at"],
            )
        ]


class EventHost(ClubScopedModel, ModelBase):
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

    @property
    def clubs(self):
        # Allow all clubs on event to edit hosts
        return self.event.clubs

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="one_primary_host_per_event",
                fields=("event", "is_primary"),
                condition=models.Q(is_primary=True),
            )
        ]


class EventAttendance(ClubScopedModel, ModelBase):
    """
    Records when user attend an event.

    It is scoped to the user level and not clubmember level
    to allow tracking of users for non-club events.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="attendances",
        # blank=True,
        # null=True,
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="event_attendances"
    )

    @property
    def clubs(self):
        return self.event.clubs

    @property
    def poll_submission(self):
        from polls.models import PollSubmission

        if not self.event.poll:
            return None

        return PollSubmission.objects.find_one(poll=self.event.poll, user=self.user)

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

    # TODO: How to handle permissions with multiple clubs and event hosts?

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="attendance_links"
    )
    reference = models.CharField(
        null=True, blank=True, help_text="Used to differentiate between links"
    )

    # Overrides
    objects: ClassVar["EventAttendanceLinkManager"] = EventAttendanceLinkManager()

    @property
    def clubs(self):
        return self.event.clubs

    def __str__(self):
        if self.reference:
            return f"{super().__str__()} ({self.reference})"
        else:
            return super().__str__()

    def save(self, *args, **kwargs):
        self.is_tracked = False  # Tracking is done on the frontend
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("event", "reference"),
                name="unique_reference_per_event_attendance_link",
            )
        ]


class EventCancellation(ClubScopedModel, ModelBase):
    """Record when an event is canceled."""

    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="cancellation"
    )
    reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    @property
    def clubs(self):
        return self.event.clubs
