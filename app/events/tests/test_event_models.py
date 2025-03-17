from django.urls import reverse
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
            name="Test event", host=primary_club, secondary_hosts=clubs
        )

        self.assertEqual(event.clubs.count(), 6)

    def test_create_event_link(self):
        """Creating an event should createa new event attendance link."""

        self.assertEqual(Link.objects.count(), 0)

        club = create_test_club()
        event = Event.objects.create(host=club, name="Test Event")

        self.assertEqual(event.attendance_links.count(), 1)
        self.assertEqual(Link.objects.count(), 1)
        link = event.attendance_links.first()

        expected_url_path = reverse("events:attendance", args=[event.id])
        expected_url = get_full_url(expected_url_path)
        self.assertEqual(link.target_url, expected_url)
