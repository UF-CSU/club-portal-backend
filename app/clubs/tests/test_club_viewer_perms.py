import pytz
from django.utils import timezone

from clubs.services import ClubService
from clubs.tests.utils import club_detail_url, create_test_club
from core.abstracts.tests import PrivateApiTestsBase
from events.models import Event
from events.tests.utils import EVENT_LIST_URL, create_test_event, event_detail_url
from lib.faker import fake
from users.tests.utils import create_test_user


class ApiClubViewerTests(PrivateApiTestsBase):
    """
    Test club viewer access to api.

    Most of these tests will probably overlap with the checks
    in the admin tests that ensure admins can only do ops on their
    own clubs, but are repeated here for clarity and in case the
    implementation drifts over time.
    """

    def create_authenticated_user(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)

        owner_user = create_test_user()
        self.service.add_member(owner_user, roles=["President"], is_owner=True)

        user = create_test_user()
        self.service.add_member(user, roles=["Member"])
        return super().create_authenticated_user()

    def test_unable_edit_club(self):
        """Viewers should not be able to edit clubs."""

        payload = {"name": self.club.name + " updated"}

        url = club_detail_url(self.club.id)
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        self.club.refresh_from_db()
        self.assertNotEqual(self.club.name, payload["name"])

    def test_unable_edit_events(self):
        """Viewers should not be able to edit events."""

        event = create_test_event(host=self.club)
        payload = {"name": event.name + " updated"}

        url = event_detail_url(event.id)
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        event.refresh_from_db()
        self.assertNotEqual(event.name, payload["name"])

    def test_unable_delete_events(self):
        """Viewers should not be able to delete events."""

        event = create_test_event(host=self.club)
        url = event_detail_url(event.id)
        res = self.client.delete(url)
        self.assertResForbidden(res)

        self.assertTrue(Event.objects.filter(id=event.id).exists())

    def test_unable_add_events(self):
        """Viewers should not be able to add events or recurring events."""

        payload = {
            "name": fake.title(),
            "description": fake.paragraph(),
            "location": fake.address(),
            "event_type": "gbm",
            "start_at": timezone.datetime(
                year=2025,
                month=7,
                day=23,
                hour=17,
                minute=0,
                tzinfo=pytz.timezone("US/Eastern"),
            ),
            "end_at": timezone.datetime(
                year=2025,
                month=7,
                day=23,
                hour=19,
                minute=0,
                tzinfo=pytz.timezone("US/Eastern"),
            ),
        }
        url = EVENT_LIST_URL

        # Event with a host
        payload["hosts"] = [self.club.id]
        res = self.client.post(url, payload, format="json")
        self.assertResForbidden(res)

        # Event without a host
        payload["hosts"] = []
        res = self.client.post(url, payload, format="json")
        self.assertResForbidden(res)
