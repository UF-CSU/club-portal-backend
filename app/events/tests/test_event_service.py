"""
Unit tests for Event business logic.
"""

import datetime

from django.utils import timezone

from clubs.models import ClubFile
from clubs.tests.utils import create_test_club, create_test_clubfile, create_test_clubs
from core.abstracts.tests import TestsBase
from events.models import DayChoice, Event, RecurringEvent
from events.services import RecurringEventService
from lib.faker import fake


class ClubEventTests(TestsBase):
    """Unit tests for club events."""

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
            "days": [DayChoice.TUESDAY, DayChoice.THURSDAY],
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
        self.assertEqual(Event.objects.count(), EXPECTED_EV_COUNT)
        self.assertEqual(rec.expected_event_count, EXPECTED_EV_COUNT)
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

        Event.objects.all().delete()
        self.assertEqual(Event.objects.count(), 0)

        RecurringEventService(rec).sync_events()
        self.assertEqual(Event.objects.count(), EXPECTED_EV_COUNT)

    def test_recurring_event_allday_events(self):
        """Recurring event template should handle all day events."""

        self.assertEqual(Event.objects.count(), 0)

        rec = RecurringEvent.objects.create(
            name=fake.title(),
            days=[DayChoice.MONDAY],
            start_date=timezone.datetime(2025, 3, 16),
            end_date=timezone.datetime(2025, 3, 18),
        )

        self.assertEqual(rec.expected_event_count, 1)
        self.assertEqual(Event.objects.count(), 1)

        ev = Event.objects.first()
        self.assertEqual(ev.start_at.weekday(), 0)
        self.assertEqual(ev.start_at.hour, 0)
        self.assertEqual(ev.start_at.minute, 0)

        self.assertEqual(ev.end_at.weekday(), 0)
        self.assertEqual(ev.end_at.hour, 23)
        self.assertEqual(ev.end_at.minute, 59)
