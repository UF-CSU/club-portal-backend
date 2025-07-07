from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from core.abstracts.tests import ViewTestsBase
from events.models import Event, EventAttendance
from lib.faker import fake
from users.tests.utils import create_test_user


def event_attendance_url(event_id: int):
    """Get url to log event attendance for member."""

    return reverse("events:attendance", kwargs={"id": event_id})


def event_attendance_done_url(event_id: int):
    """Get url to log event attendance for member."""

    return reverse("events:attendance_done", kwargs={"id": event_id})


class EventViewTests(ViewTestsBase):
    """Test cases for event views."""

    def test_join_event_view(self):
        """Should record attendance when joining event."""

        # Create user
        user = create_test_user()
        self.client.force_login(user)

        # Create event and url
        event = Event.objects.create(
            name=fake.title(3),
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
        )
        url = event_attendance_url(event_id=event.id)
        redirect_url = event_attendance_done_url(event_id=event.id)

        self.assertEqual(EventAttendance.objects.count(), 0)

        # User visits attendance url, check if it redirects
        res = self.client.get(url)
        self.assertRedirects(
            res, expected_url=redirect_url, status_code=status.HTTP_302_FOUND
        )

        # Check attendance values
        self.assertEqual(EventAttendance.objects.count(), 1)

        ea = EventAttendance.objects.first()
        self.assertEqual(ea.event.id, event.id)
        self.assertEqual(ea.user.id, user.id)
