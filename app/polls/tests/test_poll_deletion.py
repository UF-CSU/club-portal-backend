"""Tests for poll model deletion behavior."""

from clubs.tests.utils import create_test_club
from core.abstracts.tests import TestsBase
from django.utils import timezone
from events.models import Event

from polls.models import Poll
from polls.tests.utils import create_test_poll


class PollDeletionTests(TestsBase):
    """Tests for poll model deletion functionality."""

    def test_poll_deletion_sets_event_attendance_false(self):
        """Should set event.enable_attendance to False when associated poll is deleted."""

        club = create_test_club()
        poll = create_test_poll(club=club)

        # Create event with attendance enabled
        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,
        )

        # Associate the poll with the event
        event.poll = poll
        event.save()

        # Verify initial state
        event.refresh_from_db()
        self.assertTrue(event.enable_attendance)
        self.assertEqual(event.poll, poll)

        # Delete the poll
        poll.delete()

        # Refresh event from DB to see if attendance was disabled
        event.refresh_from_db()
        self.assertFalse(event.enable_attendance)
        self.assertIsNone(event.poll)

    def test_poll_deletion_with_multiple_polls(self):
        """Should only affect the event associated with the deleted poll."""

        club = create_test_club()
        poll1 = create_test_poll(club=club)
        poll2 = create_test_poll(club=club)

        # Create two events with attendance enabled
        event1 = Event.objects.create(
            name="Test event 1",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,
        )

        event2 = Event.objects.create(
            name="Test event 2",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,
        )

        # Associate polls with events
        event1.poll = poll1
        event1.save()
        event2.poll = poll2
        event2.save()

        # Verify initial state
        event1.refresh_from_db()
        event2.refresh_from_db()
        self.assertTrue(event1.enable_attendance)
        self.assertTrue(event2.enable_attendance)
        self.assertEqual(event1.poll, poll1)
        self.assertEqual(event2.poll, poll2)

        # Delete only poll1
        poll1.delete()

        # Check that only event1 had its attendance disabled
        event1.refresh_from_db()
        event2.refresh_from_db()
        self.assertFalse(event1.enable_attendance)  # Affected event
        self.assertTrue(event2.enable_attendance)  # Unaffected event
        self.assertIsNone(event1.poll)
        self.assertEqual(event2.poll, poll2)

    def test_poll_without_associated_event_not_affected(self):
        """Should not affect anything when deleting a poll not associated with an event."""

        club = create_test_club()
        poll = create_test_poll(club=club)  # Poll not associated with any event

        # Create event WITHOUT attendance enabled, so no automatic poll is created
        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=False,  # Attendance disabled
        )

        # Verify initial state - event should have no poll
        event.refresh_from_db()
        self.assertFalse(event.enable_attendance)
        self.assertIsNone(event.poll)

        # Delete the unassociated poll
        poll.delete()

        # Event should remain unchanged
        event.refresh_from_db()
        self.assertFalse(event.enable_attendance)
        self.assertIsNone(event.poll)

    def test_poll_deletion_cascades_properly(self):
        """Should properly handle poll deletion even when other related objects exist."""

        club = create_test_club()
        poll = create_test_poll(club=club)

        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,
        )

        # Associate the poll with the event
        event.poll = poll
        event.save()

        # Verify initial state
        event.refresh_from_db()
        self.assertTrue(event.enable_attendance)
        self.assertEqual(event.poll, poll)

        # Delete the poll (this should trigger the custom delete method)
        poll_pk = poll.pk
        poll.delete()

        # Verify the poll is actually deleted

        with self.assertRaises(Poll.DoesNotExist):
            Poll.objects.get(pk=poll_pk)

        # Verify event attendance was disabled
        event.refresh_from_db()
        self.assertFalse(event.enable_attendance)
        self.assertIsNone(event.poll)
