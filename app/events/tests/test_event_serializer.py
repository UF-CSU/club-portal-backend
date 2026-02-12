"""Tests for event serializers."""

from clubs.tests.utils import create_test_club
from core.abstracts.tests import TestsBase
from django.utils import timezone
from polls.tests.utils import create_test_poll

from events.models import Event
from events.serializers import EventSerializer


class EventSerializerUpdateTests(TestsBase):
    """Tests for event serializer update functionality."""

    def test_manual_disable_attendance_preserved(self):
        """Should preserve manual disable of attendance when updating other fields."""

        club = create_test_club()
        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,  # Initially enabled
        )

        # Verify attendance was initially enabled and poll was created
        event.refresh_from_db()
        self.assertTrue(event.enable_attendance)
        self.assertIsNotNone(event.poll)

        # Manually disable attendance via serializer update
        data = {"enable_attendance": False}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_event = serializer.save()

        # Refresh from DB to ensure changes are persisted
        updated_event.refresh_from_db()
        self.assertFalse(updated_event.enable_attendance)
        self.assertIsNotNone(updated_event.poll)  # Poll should remain

    def test_manual_enable_attendance_preserved(self):
        """Should preserve manual enable of attendance when updating other fields."""

        club = create_test_club()
        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=False,  # Initially disabled
        )

        # Verify attendance was initially disabled
        event.refresh_from_db()
        self.assertFalse(event.enable_attendance)
        self.assertIsNone(event.poll)

        # Manually enable attendance via serializer update
        data = {"enable_attendance": True}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_event = serializer.save()

        # Refresh from DB to ensure changes are persisted
        updated_event.refresh_from_db()
        self.assertTrue(updated_event.enable_attendance)
        self.assertIsNotNone(updated_event.poll)  # Poll should be created

    def test_update_other_fields_preserves_attendance_setting(self):
        """Should preserve attendance setting when updating other fields."""

        club = create_test_club()
        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,  # Initially enabled
        )

        # Verify attendance was initially enabled
        event.refresh_from_db()
        self.assertTrue(event.enable_attendance)
        self.assertIsNotNone(event.poll)

        # Update other fields without changing attendance
        data = {"name": "Updated event name"}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_event = serializer.save()

        # Refresh from DB to ensure changes are persisted
        updated_event.refresh_from_db()
        self.assertTrue(updated_event.enable_attendance)  # Should remain enabled
        self.assertEqual(updated_event.name, "Updated event name")
        self.assertIsNotNone(updated_event.poll)  # Poll should remain

    def test_update_attendance_and_other_fields_together(self):
        """Should properly handle updating attendance and other fields together."""

        club = create_test_club()
        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,  # Initially enabled
        )

        # Verify attendance was initially enabled
        event.refresh_from_db()
        self.assertTrue(event.enable_attendance)
        self.assertIsNotNone(event.poll)

        # Update attendance and other fields together
        data = {"name": "Updated event name", "enable_attendance": False}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_event = serializer.save()

        # Refresh from DB to ensure changes are persisted
        updated_event.refresh_from_db()
        self.assertFalse(updated_event.enable_attendance)  # Should be disabled
        self.assertEqual(updated_event.name, "Updated event name")
        self.assertIsNotNone(updated_event.poll)  # Poll should remain

    def test_update_with_poll_change_preserves_attendance(self):
        """Should preserve attendance setting when changing associated poll."""

        club = create_test_club()
        poll1 = create_test_poll(club=club)
        poll2 = create_test_poll(club=club)

        event = Event.objects.create(
            name="Test event",
            host=club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            enable_attendance=True,  # Initially enabled
        )

        # Associate first poll to event
        event.poll = poll1

        event.refresh_from_db()
        self.assertTrue(event.enable_attendance)
        self.assertEqual(event.poll, poll1)

        # Change poll via serializer while keeping attendance enabled
        data = {"poll": poll2.pk}
        serializer = EventSerializer(event, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_event = serializer.save()

        # Refresh from DB to ensure changes are persisted
        updated_event.refresh_from_db()
        self.assertTrue(updated_event.enable_attendance)  # Should remain enabled
        self.assertEqual(updated_event.poll, poll2)  # Poll should be updated
