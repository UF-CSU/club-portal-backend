from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase, PublicApiTestsBase
from events.tests.utils import (
    EVENT_LIST_URL,
    create_test_event,
    create_test_events,
    event_detail_url,
)
from users.tests.utils import create_test_user


class EventPublicApiTests(PublicApiTestsBase):
    """Events api tests for guest users."""

    def test_list_public_events(self):
        """Should list public events."""

        create_test_events(count=5)

        url = EVENT_LIST_URL
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()
        self.assertEqual(len(data), 5)

        # Check private events not in api
        create_test_events(count=5, is_public=False)
        res = self.client.get(url)
        self.assertResOk(res)
        data = res.json()
        self.assertEqual(len(data), 5)

    def test_detail_public_events(self):
        """Should return event if it's marked public."""

        e1 = create_test_event(is_public=True)
        e2 = create_test_event(is_public=False)

        url1 = event_detail_url(e1.pk)
        url2 = event_detail_url(e2.pk)

        # Returns public event
        res1 = self.client.get(url1)
        self.assertResOk(res1)

        # Returns 404 not found
        res2 = self.client.get(url2)
        self.assertResNotFound(res2)


class EventPrivateApiTests(PrivateApiTestsBase):
    """Events api tests for authenticated users."""

    def create_authenticated_user(self):
        return create_test_user()

    def test_list_events_api(self):
        """Should return list of events for assigned clubs."""

        events_count = 5

        # Setup
        c1 = create_test_club(members=[self.user])
        c2 = create_test_club()

        create_test_events(events_count, host=c1)
        create_test_events(events_count, host=c2)

        url = EVENT_LIST_URL
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        # Should return all events
        self.assertEqual(len(data), events_count * 2)

    def test_event_detail_api(self):
        """Should get single event."""

        club = create_test_club()
        event = create_test_event(host=club)

        url = event_detail_url(event.id)
        res = self.client.get(url)
        self.assertResOk(res)
