from django.urls import reverse

from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase, PublicApiTestsBase
from events.tests.utils import create_test_events

EVENTS_LIST_URL = reverse("api-events:event-list")


class EventPublicApiTests(PublicApiTestsBase):
    """Events api tests for guest users."""

    def test_events_unauthorized(self):
        """Should return 403 if accessing events without authentication."""

        create_test_events(count=5)

        url = EVENTS_LIST_URL
        res = self.client.get(url)

        self.assertResUnauthorized(res)


class EventPrivateApiTests(PrivateApiTestsBase):
    """Events api tests for authenticated users."""

    def test_list_events_api(self):
        """Should return list of events for assigned clubs."""

        events_count = 5

        # Setup
        c1 = create_test_club(members=[self.user])
        c2 = create_test_club()

        create_test_events(events_count, host=c1)
        create_test_events(events_count, host=c2)

        # Make request
        url = EVENTS_LIST_URL
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        # Should only return events from c1
        self.assertEqual(len(data), events_count)

        for event in data:
            clubs = event["hosts"]
            matches = [club for club in clubs if club["club_id"] == c1.id]
            self.assertLength(matches, 1)
