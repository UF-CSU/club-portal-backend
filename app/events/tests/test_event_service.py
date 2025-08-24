"""
Unit tests for Event business logic.
"""

import datetime

from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from freezegun import freeze_time

from clubs.models import ClubFile
from clubs.tests.utils import create_test_club, create_test_clubfile, create_test_clubs
from core.abstracts.tests import PeriodicTaskTestsBase, TestsBase
from events.models import DayType, Event, EventAttendance, RecurringEvent
from events.services import RecurringEventService
from events.tests.utils import create_test_event
from lib.faker import fake
from users.tests.utils import create_test_user


class EventServiceTests(PeriodicTaskTestsBase):
    """Unit tests for events business logic."""

    def test_make_public_at(self):
        """Should set event as public at given date."""

        pt_before = PeriodicTask.objects.count()

        event = create_test_event()
        event.is_public = False
        event.make_public_at = timezone.now() + timezone.timedelta(days=1)
        event.save()

        self.assertEqual(PeriodicTask.objects.count(), pt_before + 1)

        event.refresh_from_db()
        self.run_clocked_func(event.make_public_task)

        event.refresh_from_db()
        self.assertTrue(event.is_public)


class RecurringEventTests(TestsBase):
    """Unit tests for recurring events business logic."""

    def test_create_recurring_event(self):
        """
        Recurring event should create multiple events.

        Between 9/1/24 and 12/1/24 there are 13 tuesdays and 13 thursdays.
        """
        EXPECTED_EV_COUNT = 13 * 2  # 13 Tuesdays + 13 Thursdays
        # Expected dates are for the Tuesdays and Thursdays in the range
        # 9/1/2024 to 12/1/2024 and in the format (month, day).
        EXPECTED_DATES = [
            (9, 3),
            (9, 5),
            (9, 10),
            (9, 12),
            (9, 17),
            (9, 19),
            (9, 24),
            (9, 26),
            (10, 1),
            (10, 3),
            (10, 8),
            (10, 10),
            (10, 15),
            (10, 17),
            (10, 22),
            (10, 24),
            (10, 29),
            (10, 31),
            (11, 5),
            (11, 7),
            (11, 12),
            (11, 14),
            (11, 19),
            (11, 21),
            (11, 26),
            (11, 28),
        ]

        primary_club = create_test_club()
        files = [create_test_clubfile(club=primary_club)]

        payload = {
            "name": fake.title(),
            "start_date": timezone.datetime(2024, 9, 1),
            "end_date": timezone.datetime(2024, 12, 1),
            "days": [DayType.TUESDAY, DayType.THURSDAY],
            "event_start_time": datetime.time(17, 0, 0),
            "event_end_time": datetime.time(19, 0, 0),
            "club": primary_club,
            "other_clubs": create_test_clubs(3),
            "attachments": files,
        }

        club_files_count_before = ClubFile.objects.count()
        self.assertEqual(Event.objects.count(), 0)

        # TODO: Figure out how to handle clubs with recurring events
        rec = RecurringEvent.objects.create(**payload)
        service = RecurringEventService(rec)
        service.sync_events()

        self.assertEqual(Event.objects.count(), EXPECTED_EV_COUNT)
        self.assertEqual(rec.expected_event_count, EXPECTED_EV_COUNT)
        self.assertEqual(rec.attachments.count(), len(files))
        self.assertEqual(ClubFile.objects.count(), club_files_count_before)

        for i, event in enumerate(list(Event.objects.all().order_by("start_at"))):
            if i % 2 == 0:
                # Tuesdays
                self.assertEqual(event.start_at.weekday(), 1)
                self.assertEqual(event.end_at.weekday(), 1)
            else:
                # Thursdays
                self.assertEqual(event.start_at.weekday(), 3)
                self.assertEqual(event.end_at.weekday(), 3)

            self.assertEqual(event.name, rec.name)
            self.assertIsNone(event.description)

            # self.assertEqual(event.start_at.weekday(), 1)
            self.assertEqual(event.start_at.hour, 17)
            self.assertEqual(event.start_at.minute, 0)

            # self.assertEqual(event.end_at.weekday(), 1)
            self.assertEqual(event.end_at.hour, 19)
            self.assertEqual(event.end_at.minute, 0)

            expected_month, expected_day = EXPECTED_DATES[i]
            self.assertEqual(event.start_at.month, expected_month)
            self.assertEqual(event.start_at.day, expected_day)
            self.assertEqual(event.attachments.count(), len(files))
            self.assertEqual(event.attachments.first().pk, files[0].pk)
            self.assertEqual(event.clubs.count(), rec.other_clubs.all().count() + 1)
            self.assertEqual(event.primary_club.id, rec.club.id)

        Event.objects.all().delete()
        self.assertEqual(Event.objects.count(), 0)
        service.sync_events()

        # Check resyncing
        self.assertEqual(Event.objects.count(), EXPECTED_EV_COUNT)
        service.sync_events()
        self.assertEqual(Event.objects.count(), EXPECTED_EV_COUNT)

    def test_recurring_event_allday_events(self):
        """Recurring event template should handle all day events."""

        self.assertEqual(Event.objects.count(), 0)

        rec = RecurringEvent.objects.create(
            name=fake.title(),
            days=[DayType.MONDAY],
            start_date=timezone.datetime(2025, 3, 16),
            end_date=timezone.datetime(2025, 3, 18),
        )
        RecurringEventService(rec).sync_events()

        self.assertEqual(rec.expected_event_count, 1)
        self.assertEqual(Event.objects.count(), 1)

        ev = Event.objects.first()
        self.assertEqual(ev.start_at.weekday(), 0)
        self.assertEqual(ev.start_at.hour, 0)
        self.assertEqual(ev.start_at.minute, 0)

        self.assertEqual(ev.end_at.weekday(), 0)
        self.assertEqual(ev.end_at.hour, 23)
        self.assertEqual(ev.end_at.minute, 59)

    def test_event_name_conflicts(self):
        """Recurring events should add event even if name/times exist."""

        rec = RecurringEvent.objects.create(
            name=fake.title(),
            description=fake.sentence(),
            days=[DayType.MONDAY, DayType.WEDNESDAY],
            start_date=timezone.datetime(2025, 3, 16),
            end_date=timezone.datetime(2025, 4, 16),
        )
        service = RecurringEventService(rec)
        service.sync_events()

        # Detach event from recurring event
        event_1 = rec.events.order_by("start_at").first()
        event_1.recurring_event = None
        event_1.save()

        # Sync events
        events_count_before = Event.objects.count()
        service.sync_events()

        # Check old event
        self.assertIsNone(event_1.recurring_event)
        self.assertEqual(Event.objects.count(), events_count_before + 1)

        # Check that new event created has proper name
        event_2 = rec.events.order_by("start_at").first()

        self.assertDatesEqual(event_2.start_at, rec.start_date, skip=["day", "month"])
        self.assertDatesEqual(event_2.end_at, rec.end_date, skip=["day", "month"])
        self.assertEqual(event_2.description, rec.description)
        self.assertEqual(event_2.name, f"{rec.name} 1")

        # Check for multiple duplicated objects
        event_2.recurring_event = None
        event_2.save()
        service.sync_events()
        event_3 = rec.events.order_by("start_at").first()

        self.assertDatesEqual(event_3.start_at, rec.start_date, skip=["day", "month"])
        self.assertDatesEqual(event_3.end_at, rec.end_date, skip=["day", "month"])
        self.assertEqual(event_3.description, rec.description)
        self.assertEqual(event_3.name, f"{rec.name} 2")

    def test_delete_extra_events(self):
        """Should delete extra events."""

        # 2 Mondays, 2 Wednesdays between 7/20/25 - 8/2/25
        rec = RecurringEvent.objects.create(
            name=fake.title(),
            description=fake.sentence(),
            days=[DayType.MONDAY, DayType.WEDNESDAY],
            start_date=timezone.datetime(2025, 7, 20),
            end_date=timezone.datetime(2025, 8, 2),
        )
        service = RecurringEventService(rec)
        service.sync_events()

        expected_count_before = rec.expected_event_count
        self.assertEqual(expected_count_before, 4)
        self.assertEqual(Event.objects.count(), expected_count_before)

        # Check 1 less day
        rec.days = [DayType.MONDAY]
        rec.save()
        rec.refresh_from_db()

        service.sync_events()

        expected_count_after = rec.expected_event_count
        self.assertEqual(expected_count_after, 2)
        self.assertEqual(Event.objects.count(), expected_count_after)

        # Check different times
        rec.event_start_time = datetime.time(hour=17, minute=0, second=0)
        rec.event_end_time = datetime.time(hour=18, minute=0, second=0)
        rec.save()
        rec.refresh_from_db()
        service.refresh_from_db()
        service.sync_events()

        self.assertEqual(Event.objects.count(), expected_count_after)

        for event in Event.objects.all():
            self.assertEqual(event.start_at.hour, 17)
            self.assertEqual(event.end_at.hour, 18)

        rec.event_start_time = datetime.time(hour=18, minute=0, second=0)
        rec.event_end_time = datetime.time(hour=19, minute=0, second=0)
        rec.save()
        service.refresh_from_db()
        service.sync_events()

        self.assertEqual(Event.objects.count(), expected_count_after)

        for event in Event.objects.all():
            self.assertEqual(event.start_at.hour, 18)
            self.assertEqual(event.end_at.hour, 19)

    def test_multi_day_events(self):
        """Should properly create events that stretch multiple days."""

        rec = RecurringEvent.objects.create(
            name=fake.title(),
            description=fake.sentence(),
            days=[DayType.MONDAY, DayType.WEDNESDAY],
            start_date=timezone.datetime(2025, 7, 20),
            end_date=timezone.datetime(2025, 8, 2),
            event_start_time=datetime.time(hour=23, minute=0, second=0),
            event_end_time=datetime.time(hour=1, minute=0, second=0),
        )
        service = RecurringEventService(rec)
        service.sync_events()

        event = Event.objects.first()
        self.assertEqual(event.recurring_event.id, rec.id)

        self.assertDatesEqual(
            event.start_at, datetime.datetime(2025, 7, 21, hour=23, minute=0, second=0)
        )
        self.assertDatesEqual(
            event.end_at, datetime.datetime(2025, 7, 22, hour=1, minute=0, second=0)
        )

        # Check resyncing events
        count_before = Event.objects.count()
        service.sync_events()
        service.sync_events()
        service.sync_events()

        self.assertEqual(Event.objects.count(), count_before)

    def test_syncing_events_deleting_event_data(self):
        """When syncing events, should be careful when deleting events."""

        # 2 Mondays, 2 Wednesdays between 7/20/25 - 8/2/25
        rec = RecurringEvent.objects.create(
            name=fake.title(),
            description=fake.sentence(),
            days=[DayType.MONDAY, DayType.WEDNESDAY],
            start_date=timezone.datetime(2025, 7, 20),
            end_date=timezone.datetime(2025, 8, 2),
            event_start_time=datetime.time(hour=18, minute=0, second=0),
            event_end_time=datetime.time(hour=19, minute=0, second=0),
        )
        service = RecurringEventService(rec)
        service.sync_events()

        expected_count = Event.objects.count()

        # User attends event
        u1 = create_test_user()
        e1 = Event.objects.first()
        EventAttendance.objects.create(event=e1, user=u1)

        self.assertEqual(e1.attendances.count(), 1)

        # Recurring event updates
        rec.event_start_time = datetime.time(hour=17, minute=0, second=0)
        rec.event_end_time = datetime.time(hour=18, minute=0, second=0)
        rec.save()

        service.refresh_from_db()
        service.sync_events()
        self.assertEqual(Event.objects.count(), expected_count)

        # Make sure event still exists
        self.assertTrue(Event.objects.filter(id=e1.pk).exists())
        self.assertTrue(e1.attendances.count(), 1)

    @freeze_time("2025-08-03")
    # @patch("django.utils.timezone.now")
    def test_sync_events_prevent_past_updates(self):
        """Should not update/delete past events."""

        # Sanity check
        self.assertDatesEqual(timezone.now(), timezone.datetime(2025, 8, 3))

        # Setup data
        rec_start = timezone.datetime(year=2025, month=7, day=20)
        rec_end = timezone.datetime(year=2025, month=8, day=17)

        name1 = fake.title()
        desc1 = fake.paragraph()
        start1 = datetime.time(hour=17, minute=0)
        end1 = datetime.time(hour=19, minute=0)

        # 2 tues/thurs before, 2 after
        rec = RecurringEvent.objects.create(
            name=name1,
            description=desc1,
            days=[DayType.TUESDAY, DayType.THURSDAY],
            start_date=rec_start,
            end_date=rec_end,
            event_start_time=start1,
            event_end_time=end1,
            prevent_sync_past_events=True,
        )
        service = RecurringEventService(rec)
        service.sync_events()

        # Update recurring
        name2 = fake.title()
        desc2 = fake.paragraph()
        start2 = datetime.time(hour=17, minute=0)
        end2 = datetime.time(hour=19, minute=0)

        rec.days = [DayType.TUESDAY]  # Remove a day
        rec.name = name2
        rec.description = desc2
        rec.event_start_time = start2
        rec.event_end_time = end2
        rec.start_date = timezone.datetime(year=2025, month=7, day=27)
        rec.save()

        # Resync events
        service.refresh_from_db()
        service.sync_events()

        # Check past Thursdays weren't deleted
        past_thursday_events = (
            Event.objects.filter_for_day(DayType.THURSDAY)
            .filter(recurring_event=rec)
            .filter(start_at__date__lt=timezone.now())
        )
        self.assertTrue(past_thursday_events.exists())
        self.assertEqual(past_thursday_events.count(), 2)

        # Check past events weren't updated
        past_events = Event.objects.filter(
            recurring_event=rec, start_at__date__lt=timezone.now()
        ).all()
        self.assertEqual(past_events.count(), 4)  # 2 Tuesdays + 2 Thursdays
        for event in past_events:
            self.assertEqual(event.name, name1)
            self.assertEqual(event.description, desc1)
            self.assertEqual(event.start_at.time(), start1)
            self.assertEqual(event.end_at.time(), end1)

        # Check future Thursdays were deleted
        future_thursday_events = (
            Event.objects.filter_for_day(DayType.THURSDAY)
            .filter(recurring_event=rec)
            .filter(start_at__date__gt=timezone.now())
        )
        self.assertFalse(future_thursday_events.exists())

        # Check future Tuesdays were updated
        future_events = Event.objects.filter(
            recurring_event=rec, start_at__date__gt=timezone.now()
        ).all()
        self.assertEqual(future_events.count(), 2)  # 2 Tuesdays
        for event in future_events:
            self.assertEqual(event.name, name2)
            self.assertEqual(event.description, desc2)
            self.assertEqual(event.start_at.time(), start2)
            self.assertEqual(event.end_at.time(), end2)
