from datetime import timedelta

from django.utils import timezone

from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase, PublicApiTestsBase
from events.tests.utils import (
    EVENT_LIST_URL,
    create_test_event,
    create_test_events,
    event_detail_url,
    event_list_url,
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

    def test_get_default_filtering(self):
        """Should get events from two weeks ago and two weeks into the future"""

        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_event_time = today.replace(hour=12)
        shift = timedelta(days=14)

        events_in_range = 8

        # Create test club
        club = create_test_club()

        # Create events where:
        # 1 events are on the day of boundary
        create_test_event(
            host=club,
            start_at=today_event_time - shift,
            end_at=(today_event_time - shift) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + shift - timedelta(days=1),
            end_at=(today_event_time + shift) + timedelta(hours=1) - timedelta(days=1),
        )
        # 2 events are one day between range
        create_test_event(
            host=club,
            start_at=today_event_time,
            end_at=today_event_time + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=7),
            end_at=today_event_time - timedelta(days=7) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=7),
            end_at=today_event_time + timedelta(days=7, hours=1),
        )
        # 3 events are outside range (1 right outside and one way outside)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=15),
            end_at=today_event_time + timedelta(days=15, hours=1),
        )

        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=30),
            end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=30),
            end_at=today_event_time + timedelta(days=30, hours=1),
        )

        # event that starts within range but ends outside
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=7),
            end_at=today_event_time + timedelta(days=15),
        )

        # event that starts outside range but ends inside
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=7),
        )

        # event that starts outside range and ends outside range
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time + timedelta(days=15),
        )

        url = EVENT_LIST_URL
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), events_in_range)

    def test_get_start_filter(self):
        """Should get events from one week ago and two weeks into the future"""
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_event_time = today.replace(hour=12)
        shift = timedelta(days=14)
        mod_shift = timedelta(days=7)

        events_in_range = 8

        # Create test club
        club = create_test_club()

        # Create events where:
        # 1 events are on the day of boundary (1 valid, 1 invalid)
        create_test_event(
            host=club,
            start_at=today_event_time - shift,
            end_at=(today_event_time - shift) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + shift - timedelta(days=1),
            end_at=(today_event_time + shift) + timedelta(hours=1) - timedelta(days=1),
        )
        # 2 events are one day between range (3 valid)
        create_test_event(
            host=club,
            start_at=today_event_time,
            end_at=today_event_time + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=7),
            end_at=today_event_time - timedelta(days=7) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=7),
            end_at=today_event_time + timedelta(days=7, hours=1),
        )

        # 3 events are outside range (4 invalid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=15),
            end_at=today_event_time + timedelta(days=15, hours=1),
        )

        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=30),
            end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=30),
            end_at=today_event_time + timedelta(days=30, hours=1),
        )

        # event that starts within range but ends outside (1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=7),
            end_at=today_event_time + timedelta(days=15),
        )

        # event that starts outside range but ends inside (1 invalid, 1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=7),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=7),
            end_at=today_event_time + timedelta(days=8),
        )

        # event that starts outside range and ends outside range (1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time + timedelta(days=15),
        )

        url = event_list_url(today - mod_shift)
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), events_in_range)

    def test_get_end_filter(self):
        """Should get events from two weeks ago and one week into the future"""
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_event_time = today.replace(hour=12)
        shift = timedelta(days=14)
        mod_shift = timedelta(days=7)

        events_in_range = 8

        # Create test club
        club = create_test_club()

        # Create events where:
        # 1 events are on the day of boundary (2 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - shift,
            end_at=(today_event_time - shift) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + mod_shift - timedelta(days=1),
            end_at=(today_event_time + mod_shift)
            + timedelta(hours=1)
            - timedelta(days=1),
        )
        # 2 events are one day between range (3 valid)
        create_test_event(
            host=club,
            start_at=today_event_time,
            end_at=today_event_time + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=7),
            end_at=today_event_time - timedelta(days=7) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=6),
            end_at=today_event_time + timedelta(days=6, hours=1),
        )

        # 3 events are outside range (4 invalid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=15),
            end_at=today_event_time + timedelta(days=15, hours=1),
        )

        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=30),
            end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=30),
            end_at=today_event_time + timedelta(days=30, hours=1),
        )

        # event that starts within range but ends outside (1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=7),
            end_at=today_event_time + timedelta(days=15),
        )

        # event that starts outside range but ends inside (2 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=7),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=7),
            end_at=today_event_time + timedelta(days=8),
        )

        # event that starts outside range and ends outside range (1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time + timedelta(days=15),
        )

        url = event_list_url(end_at=today + mod_shift)
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), events_in_range)

    def test_get_both_filters(self):
        """Should get events from one week ago to one week into the future"""
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_event_time = today.replace(hour=12)
        timedelta(days=14)
        mod_shift = timedelta(days=7)

        events_in_range = 8

        # Create test club
        club = create_test_club()

        # Create events where:
        # 1 events are on the day of boundary (1 valid, 1 invalid)
        create_test_event(
            host=club,
            start_at=today_event_time - mod_shift,
            end_at=(today_event_time - mod_shift) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + mod_shift - timedelta(days=1),
            end_at=(today_event_time + mod_shift)
            + timedelta(hours=1)
            - timedelta(days=1),
        )
        # 2 events are one day between range (3 valid)
        create_test_event(
            host=club,
            start_at=today_event_time,
            end_at=today_event_time + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=3),
            end_at=today_event_time - timedelta(days=3) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=3),
            end_at=today_event_time + timedelta(days=3, hours=1),
        )

        # 3 events are outside range (4 invalid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=15),
            end_at=today_event_time + timedelta(days=15, hours=1),
        )

        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=30),
            end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
        )
        create_test_event(
            host=club,
            start_at=today_event_time + timedelta(days=30),
            end_at=today_event_time + timedelta(days=30, hours=1),
        )

        # event that starts within range but ends outside (1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=2),
            end_at=today_event_time + timedelta(days=15),
        )

        # event that starts outside range but ends inside (2 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=8),
            end_at=today_event_time + timedelta(days=5),
        )

        # event that starts outside range and ends outside range (1 valid)
        create_test_event(
            host=club,
            start_at=today_event_time - timedelta(days=15),
            end_at=today_event_time + timedelta(days=15),
        )

        url = event_list_url(today - mod_shift, today + mod_shift)
        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), events_in_range)
