from django.urls import reverse
from django.utils import timezone

from analytics.models import Link
from clubs.tests.utils import create_test_club, create_test_clubs
from core.abstracts.tests import TestsBase
from events.models import Event
from utils.helpers import get_full_url


class ClubEventTests(TestsBase):
    """Unit tests for club events."""

    def test_event_hosts(self):
        """Getting event hosts should return all clubs hosting event."""

        primary_club = create_test_club()
        clubs = create_test_clubs(5)

        event = Event.objects.create(
            name="Test event",
            host=primary_club,
            secondary_hosts=clubs,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
        )

        self.assertEqual(event.clubs.count(), 6)

    def test_create_event_link(self):
        """Creating an event should createa new event attendance link."""

        self.assertEqual(Link.objects.count(), 0)

        club = create_test_club()
        event = Event.objects.create(
            host=club,
            name="Test Event",
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
        )

        self.assertEqual(event.attendance_links.count(), 1)
        self.assertEqual(Link.objects.count(), 1)
        link = event.attendance_links.first()

        expected_url_path = reverse("events:attendance", args=[event.id])
        expected_url = get_full_url(expected_url_path)
        self.assertEqual(link.target_url, expected_url)

    def test_get_events_for_club(self):
        """Event manager should only return events for specific club."""

        clubs = list(create_test_clubs(5))
        c0 = clubs[0]
        c1 = clubs[1]
        c2 = clubs[2]
        c3 = clubs[3]
        c4 = clubs[4]

        Event.objects.create(
            host=c0,
            name="Test Event",
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            clubs=[c1, c2],
        )
        Event.objects.create(
            host=c1,
            name="Test Event",
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            clubs=[c2, c3],
        )

        self.assertEqual(Event.objects.for_club(c0).count(), 1)
        self.assertEqual(Event.objects.for_club(c1).count(), 2)
        self.assertEqual(Event.objects.for_club(c2).count(), 2)
        self.assertEqual(Event.objects.for_club(c3).count(), 1)
        self.assertEqual(Event.objects.for_club(c4).count(), 0)

        # TODO: Test actual return values
