from django.utils import timezone

from analytics.models import Link
from app.settings import EVENT_ATTENDANCE_REDIRECT_URL
from clubs.tests.utils import create_test_club, create_test_clubs
from core.abstracts.tests import TestsBase
from events.models import Event
from events.serializers import EventSerializer
from polls.tests.utils import create_test_poll


class ClubEventTests(TestsBase):
    """Unit tests for club events."""

    def test_create_event_with_attendance(self):
        """Should create an event and attendance poll."""

        primary_club = create_test_club()
        event = Event.objects.create(
            name="Test event",
            host=primary_club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,
        )
        event.refresh_from_db()
        self.assertIsNotNone(event.poll)

    def test_create_event_without_attendance(self):
        """Should not create poll for event if attendance not enabled."""

        primary_club = create_test_club()
        event = Event.objects.create(
            name="Test event",
            host=primary_club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=False,
        )
        event.refresh_from_db()
        self.assertIsNone(event.poll)

    # def test_event_serializer_with_poll(self):
    #     """Should create an event using a nested poll."""

    #     primary_club = create_test_club()
    #     poll = create_test_poll(club=primary_club)
    #     # poll_data = {"name": "Test Poll", "club": primary_club.pk}

    #     data = {
    #         "name": "Test Event",
    #         "hosts": [{"club_id": primary_club.pk, "is_primary": True}],
    #         "poll": poll.id,
    #     }

    #     serializer = EventSerializer(data=data)
    #     self.assertTrue(serializer.is_valid(), serializer.errors)
    #     event = serializer.save()

    #     self.assertIsNotNone(event.poll)
    #     self.assertEqual(event.poll.name, poll_data["name"])

    def test_event_serializer_with_existing_poll(self):
        """Should create an event using an existing poll ID."""

        primary_club = create_test_club()
        poll = create_test_poll()

        data = {
            "name": "Test Event",
            "hosts": [{"club_id": primary_club.pk, "is_primary": True}],
            "poll": poll.pk,
        }

        serializer = EventSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        self.assertEqual(event.poll, poll)

    def test_event_serializer_update_poll(self):
        """Should change the poll associated with an event"""

        primary_club = create_test_club()
        poll1 = create_test_poll()
        poll2 = create_test_poll()

        event = Event.objects.create(
            name="Test event",
            host=primary_club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=False,
        )
        poll1.event = event
        poll1.save()

        self.assertEqual(event.poll, poll1)
        self.assertEqual(poll1.event, event)
        self.assertIsNone(poll2.event)

        data = {"poll": poll2.pk}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        event.refresh_from_db()
        poll1.refresh_from_db()
        poll2.refresh_from_db()
        self.assertEqual(event.poll, poll2)
        self.assertEqual(poll2.event, event)
        self.assertIsNone(poll1.event)

    def test_event_serializer_remove_poll(self):
        """Should remove the poll associated with an event"""

        primary_club = create_test_club()
        poll = create_test_poll()

        event = Event.objects.create(
            name="Test event",
            host=primary_club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=False,
        )
        poll.event = event
        poll.save()

        self.assertEqual(event.poll, poll)
        self.assertEqual(poll.event, event)

        data = {"poll": None}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        event.refresh_from_db()
        self.assertIsNone(event.poll)

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
            enable_attendance=False,
        )
        self.assertEqual(event.attendance_links.count(), 0)

        event.enable_attendance = True
        event.save()
        event.refresh_from_db()

        self.assertEqual(event.attendance_links.count(), 1)
        # TODO: Should this create a link for a poll and an event?
        self.assertEqual(Link.objects.count(), 2)
        link = event.attendance_links.first()

        # expected_url_path = reverse("api-events:attendance-list", args=[event.id])
        # expected_url = get_full_url(expected_url_path)
        expected_url = EVENT_ATTENDANCE_REDIRECT_URL % {"id": event.id}

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
            secondary_hosts=[c1, c2],
        )
        Event.objects.create(
            host=c1,
            name="Test Event",
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            secondary_hosts=[c2, c3],
        )

        self.assertEqual(Event.objects.for_club(c0).count(), 1)
        self.assertEqual(Event.objects.for_club(c1).count(), 2)
        self.assertEqual(Event.objects.for_club(c2).count(), 2)
        self.assertEqual(Event.objects.for_club(c3).count(), 1)
        self.assertEqual(Event.objects.for_club(c4).count(), 0)

        # TODO: Test actual return values
