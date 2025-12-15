from clubs.services import ClubService
from clubs.tests.utils import create_test_club
from core.abstracts.tests import (
    APIClientWrapper,
    PrivateApiTestsBase,
    PublicApiTestsBase,
)
from polls.tests.utils import create_test_poll
from users.tests.utils import create_test_adminuser, create_test_user

from events.tests.utils import (
    EVENT_LIST_URL,
    create_test_event,
    create_test_events,
    event_detail_url,
)


class EventAnalyticsPublicApiTests(PublicApiTestsBase):
    """Event analytics test for public viewing"""

    def test_list_events_analytics_api(self):
        """Should error if user is not logged in"""

        events_count = 3

        # Setup
        c1 = create_test_club()
        create_test_events(events_count, host=c1)

        url = EVENT_LIST_URL
        res = self.client.get(url)

        self.assertResUnauthorized(res)

    def test_retrieve_events_analytics_api(self):
        """Should error if user is not logged in"""

        c1 = create_test_club()
        e1 = create_test_event(host=c1)

        url = event_detail_url(e1.pk)
        res = self.client.get(url)

        self.assertResUnauthorized(res)


class EventAnalyticsPrivateApiTests(PrivateApiTestsBase):
    """Event analytics test for base logged in viewing"""

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClientWrapper()
        self.client.force_authenticate(self.user)
        return self.user

    def test_list_events_analytics_api(self):
        """Should list analytics for logged in user"""

        events_count = 3

        # Not part of respective club
        c1 = create_test_club()
        create_test_events(events_count, host=c1)

        url = EVENT_LIST_URL
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), 0)

        # Part of club
        c2 = create_test_club(members=[self.user])
        create_test_events(events_count, host=c2)

        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), 3)

        # No analytics permissions
        res = self.client.get(url + "?analytics=true")

        self.assertResOk(res)
        data = res.json()

        self.assertIn("analytics", data[0])
        self.assertIn("permissions", data[0])
        self.assertEqual(data[0]["analytics"], None)
        self.assertEqual(data[0]["permissions"]["can_view_analytics"], False)
        self.assertEqual(len(data), 3)

        # No analytics
        res = self.client.get(url + "?analytics=false")

        self.assertResOk(res)
        data = res.json()

        self.assertNotIn("analytics", data[0])
        self.assertEqual(len(data), 3)

        # Analytics allowed
        self.user = create_test_adminuser()
        self.client.force_authenticate(user=self.user)

        c3 = create_test_club(admins=[self.user])
        create_test_events(events_count, host=c3)

        svc = ClubService(c3)
        role = c3.roles.get(name="President")

        svc.set_member_role(self.user, role)

        res = self.client.get(url + "?analytics=true")

        self.assertResOk(res)
        data = res.json()

        self.assertIn("total_attended_users", data[0]["analytics"])
        self.assertEqual(data[0]["analytics"]["total_attended_users"], 0)
        self.assertEqual(len(data), 3)

    def test_retrieve_events_analytics_api(self):
        """Should retrieve analytics for logged user"""

        # Should error without perms and not requesting them
        c1 = create_test_club()
        e1 = create_test_event(c1)

        url = event_detail_url(e1.pk)
        res = self.client.get(url + "?analytics=false")

        self.assertResNotFound(res)

        # Should not find analytics without perms and requesting them
        c2 = create_test_club(members=[self.user])
        e2 = create_test_event(c2)

        url = event_detail_url(e2.pk)
        res = self.client.get(url + "?analytics=true")

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(data["analytics"], None)
        self.assertEqual(data["permissions"]["can_view_analytics"], False)

        # Should find analytics with perms and requesting them
        self.user = create_test_adminuser()
        self.client.force_authenticate(user=self.user)

        c3 = create_test_club(admins=[self.user])
        e3 = create_test_event(c3)

        svc = ClubService(c3)
        role = c3.roles.get(name="President")

        svc.set_member_role(self.user, role)

        url = event_detail_url(e3.pk)
        res = self.client.get(url + "?analytics=true")

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(data["analytics"]["total_attended_users"], 0)
        self.assertEqual(data["permissions"]["can_view_analytics"], True)

        # Should add attendances to analytics as they are created
        e3.attendances.create(user=self.user)
        e3.attendances.create(user=create_test_user())

        res = self.client.get(url + "?analytics=true")

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(data["analytics"]["total_attended_users"], 2)
        self.assertEqual(data["analytics"]["total_poll_submissions"], 0)

        # Should add polls to analytics as they are created
        p1 = create_test_poll()
        e3.poll = p1
        e3.submissions.create(poll=p1, user=self.user)

        res = self.client.get(url + "?analytics=true")

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(data["analytics"]["total_attended_users"], 2)
        self.assertEqual(data["analytics"]["total_poll_submissions"], 1)
