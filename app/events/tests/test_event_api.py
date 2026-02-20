from datetime import timedelta

import freezegun
from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase, PublicApiTestsBase
from django.utils import timezone
from polls.tests.utils import polls_detail_url
from users.tests.utils import create_test_user
from utils.helpers import reverse_query

from events.models import Event
from events.serializers import EventSerializer
from events.tests.utils import (
    EVENT_LIST_URL,
    EVENTPREVIEW_LIST_URL,
    create_test_event,
    create_test_events,
    create_test_eventtag,
    event_detail_url,
    event_list_url,
    event_preview_detail_url,
)


class EventPublicApiTests(PublicApiTestsBase):
    """Events api tests for guest users."""

    def setUp(self):
        super().setUp()
        # self.set_user_timezone("UTC")

    def test_list_public_events(self):
        """Should error on list public events."""

        create_test_events(count=5)

        url = EVENT_LIST_URL
        res = self.client.get(url)

        self.assertResUnauthorized(res)

        # Check private events not in api
        create_test_events(count=5, is_public=False)
        res = self.client.get(url)
        self.assertResUnauthorized(res)

    def test_detail_public_events(self):
        """Should error on detail public events"""

        e1 = create_test_event(is_public=True)
        e2 = create_test_event(is_public=False)

        url1 = event_detail_url(e1.pk)
        url2 = event_detail_url(e2.pk)

        # Returns public event
        res1 = self.client.get(url1)
        self.assertResUnauthorized(res1)

        # Returns 404 not found
        res2 = self.client.get(url2)
        self.assertResUnauthorized(res2)

    def test_list_event_previews(self):
        """Should display preview version of public events."""

        e1 = create_test_event(is_public=True)
        create_test_event(is_public=False)
        create_test_event(is_draft=True)

        url = EVENTPREVIEW_LIST_URL

        # Returns public event
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        assert len(data["results"]) == 1

        event = data["results"][0]
        assert event["id"] == e1.pk
        assert "attendance_links" not in event
        assert "attachments" not in event
        assert "poll" not in event
        assert "enable_attendance" not in event
        assert "make_public_at" not in event

    def test_detail_event_preview(self):
        """Should only show event preview if event is public and not draft."""

        e1 = create_test_event(is_public=True)
        e2 = create_test_event(is_public=False)
        e3 = create_test_event(is_draft=True)

        url1 = event_preview_detail_url(e1.pk)
        url2 = event_preview_detail_url(e2.pk)
        url3 = event_preview_detail_url(e3.pk)

        # Returns public event
        res1 = self.client.get(url1)
        self.assertResOk(res1)

        # Returns 404 not found if not public
        res2 = self.client.get(url2)
        self.assertResNotFound(res2)

        # Returns 404 not found if is draft
        res3 = self.client.get(url3)
        self.assertResNotFound(res3)

    @freezegun.freeze_time("11/22/25 13:00:00")
    def test_list_event_preview_default_pagination(self):
        """
        Should only show events for the next 7 days by default.
        This counts "today" as day 0, so 8 days are included in the response.
        """

        # Yesterday event, invalid
        e1 = create_test_event(start_at="11/21/25 17:00:00", end_at="11/21/25 19:00:00")
        # Today event, valid
        e2 = create_test_event(start_at="11/22/25 17:00:00", end_at="11/22/25 19:00:00")
        # Tomorrow event, valid
        e3 = create_test_event(start_at="11/23/25 17:00:00", end_at="11/23/25 19:00:00")
        # In 5 days event (inclusive), valid
        e4 = create_test_event(start_at="11/27/25 17:00:00", end_at="11/27/25 19:00:00")
        # In 6 days event, valid
        e5 = create_test_event(start_at="11/28/25 17:00:00", end_at="11/28/25 19:00:00")
        # In 7 days event, valid
        e6 = create_test_event(start_at="11/29/25 17:00:00", end_at="11/29/25 19:00:00")
        # In 8 days event, invalid
        e7 = create_test_event(start_at="11/30/25 17:00:00", end_at="11/30/25 19:00:00")

        # Check api response
        url = EVENTPREVIEW_LIST_URL
        res = self.client.get(url)
        self.assertResOk(res)

        # Check paginated response
        data = res.json()
        self.assertEqual(data["start_date"], "2025-11-22")
        self.assertEqual(data["end_date"], "2025-11-29")  # includes 7th day
        self.assertEqual(data["count"], 5)

        # Check events returned
        events = data["results"]
        self.assertEqual(len(events), 5)

        for event in events:
            self.assertNotIn(event["id"], [e1.pk, e7.pk])
            self.assertIn(event["id"], [e2.pk, e3.pk, e4.pk, e5.pk, e6.pk])

    @freezegun.freeze_time("11/24/25 13:00:00")
    def test_list_event_previews_date_range(self):
        """Should only display events in date range."""

        oct_tag = create_test_eventtag(name="October Event")
        nov_tag = create_test_eventtag(name="November Event")
        dec_tag = create_test_eventtag(name="December Event")

        # October events
        create_test_event(
            start_at="10/21/25 17:00:00", end_at="10/21/25 19:00:00", tags=[oct_tag]
        )
        create_test_event(
            start_at="10/23/25 17:00:00", end_at="10/23/25 19:00:00", tags=[oct_tag]
        )
        create_test_event(
            start_at="10/27/25 17:00:00", end_at="10/30/25 19:00:00", tags=[oct_tag]
        )

        # November events (current month)
        create_test_event(
            start_at="11/4/25 17:00:00", end_at="11/4/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/6/25 17:00:00", end_at="11/6/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/11/25 17:00:00", end_at="11/11/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/13/25 17:00:00", end_at="11/13/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/18/25 17:00:00", end_at="11/18/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/20/25 17:00:00", end_at="11/20/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/25/25 17:00:00", end_at="11/25/25 19:00:00", tags=[nov_tag]
        )
        create_test_event(
            start_at="11/27/25 17:00:00", end_at="11/27/25 19:00:00", tags=[nov_tag]
        )

        # December events
        create_test_event(
            start_at="12/2/25 17:00:00", end_at="12/2/25 19:00:00", tags=[dec_tag]
        )
        create_test_event(
            start_at="12/4/25 17:00:00", end_at="12/4/25 19:00:00", tags=[dec_tag]
        )
        create_test_event(
            start_at="12/8/25 17:00:00", end_at="12/8/25 19:00:00", tags=[dec_tag]
        )
        create_test_event(
            start_at="12/11/25 17:00:00", end_at="12/11/25 19:00:00", tags=[dec_tag]
        )

        # Check api response
        url = EVENTPREVIEW_LIST_URL + "?start_date=2025-11-01&end_date=2025-11-30"
        res = self.client.get(url)
        self.assertResOk(res)

        # Check paginated response
        data = res.json()
        self.assertEqual(data["start_date"], "2025-11-01")
        self.assertEqual(data["end_date"], "2025-11-30")  # 7 days inclusive
        self.assertEqual(data["count"], 8)

        # Check events returned
        events = data["results"]
        self.assertEqual(len(events), 8)

        november_events = nov_tag.events.all().values_list("id", flat=True)

        for event in events:
            self.assertIn(event["id"], november_events)


class EventPublicTzApiTests(PublicApiTestsBase):
    """Public API tests that include timezones."""

    @freezegun.freeze_time("11/25/25 23:00:00-05:00")
    def test_event_list_user_timezone(self):
        """Should interpret date params as user's timezone."""

        self.set_user_timezone("America/New_York")
        url = EVENTPREVIEW_LIST_URL
        res = self.client.get(url)

        data = res.json()

        self.assertEqual(data["start_date"], "2025-11-25")
        self.assertEqual(data["end_date"], "2025-12-02")


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
        data: list[EventSerializer] = res.json()["results"]

        # Should return all events for user's club
        self.assertEqual(len(data), events_count)
        self.assertEqual(data[0]["hosts"][0]["club_id"], c1.pk)

    def test_event_detail_api(self):
        """Should get single event."""

        club = create_test_club(members=[self.user])
        event = create_test_event(host=club)

        url = event_detail_url(event.id)
        res = self.client.get(url)
        self.assertResOk(res)

    # TODO: Change shift from 14 days to 7
    # def test_get_default_filtering(self):
    #     """Should get events from two weeks ago and two weeks into the future"""

    #     today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    #     today_event_time = today.replace(hour=12)
    #     shift = timedelta(days=14)

    #     events_in_range = 8

    #     # Create test club
    #     club = create_test_club(members=[self.user])

    #     # Create events where:
    #     # 1 events are on the day of boundary
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - shift,
    #         end_at=(today_event_time - shift) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + shift - timedelta(days=1),
    #         end_at=(today_event_time + shift) + timedelta(hours=1) - timedelta(days=1),
    #     )
    #     # 2 events are one day between range
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time,
    #         end_at=today_event_time + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=7),
    #         end_at=today_event_time - timedelta(days=7) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=7, hours=1),
    #     )
    #     # 3 events are outside range (1 right outside and one way outside)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=15),
    #         end_at=today_event_time + timedelta(days=15, hours=1),
    #     )

    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=30),
    #         end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=30),
    #         end_at=today_event_time + timedelta(days=30, hours=1),
    #     )

    #     # event that starts within range but ends outside
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=15),
    #     )

    #     # event that starts outside range but ends inside
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time - timedelta(days=7),
    #     )

    #     # event that starts outside range and ends outside range
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time + timedelta(days=15),
    #     )

    #     url = EVENT_LIST_URL
    #     res = self.client.get(url)

    #     self.assertResOk(res)
    #     data = res.json()["results"]

    #     self.assertEqual(len(data), events_in_range)

    # def test_get_start_filter(self):
    #     """Should get events from one week ago and two weeks into the future"""
    #     today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    #     today_event_time = today.replace(hour=12)
    #     shift = timedelta(days=14)
    #     mod_shift = timedelta(days=7)

    #     events_in_range = 8

    #     # Create test club
    #     club = create_test_club(members=[self.user])

    #     # Create events where:
    #     # 1 events are on the day of boundary (1 valid, 1 invalid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - shift,
    #         end_at=(today_event_time - shift) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + shift - timedelta(days=1),
    #         end_at=(today_event_time + shift) + timedelta(hours=1) - timedelta(days=1),
    #     )
    #     # 2 events are one day between range (3 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time,
    #         end_at=today_event_time + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=7),
    #         end_at=today_event_time - timedelta(days=7) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=7, hours=1),
    #     )

    #     # 3 events are outside range (4 invalid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=15),
    #         end_at=today_event_time + timedelta(days=15, hours=1),
    #     )

    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=30),
    #         end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=30),
    #         end_at=today_event_time + timedelta(days=30, hours=1),
    #     )

    #     # event that starts within range but ends outside (1 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=15),
    #     )

    #     # event that starts outside range but ends inside (1 invalid, 1 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time - timedelta(days=7),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=8),
    #     )

    #     # event that starts outside range and ends outside range (1 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time + timedelta(days=15),
    #     )

    #     url = event_list_url(today - mod_shift)
    #     res = self.client.get(url)

    #     self.assertResOk(res)
    #     data = res.json()["results"]

    #     self.assertEqual(len(data), events_in_range)

    # def test_get_end_filter(self):
    #     """Should get events from two weeks ago and one week into the future"""
    #     today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    #     today_event_time = today.replace(hour=12)
    #     shift = timedelta(days=14)
    #     mod_shift = timedelta(days=7)

    #     events_in_range = 8

    #     # Create test club
    #     club = create_test_club(members=[self.user])

    #     # Create events where:
    #     # 1 events are on the day of boundary (2 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - shift,
    #         end_at=(today_event_time - shift) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + mod_shift - timedelta(days=1),
    #         end_at=(today_event_time + mod_shift)
    #         + timedelta(hours=1)
    #         - timedelta(days=1),
    #     )
    #     # 2 events are one day between range (3 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time,
    #         end_at=today_event_time + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=7),
    #         end_at=today_event_time - timedelta(days=7) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=6),
    #         end_at=today_event_time + timedelta(days=6, hours=1),
    #     )

    #     # 3 events are outside range (4 invalid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time - timedelta(days=15) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=15),
    #         end_at=today_event_time + timedelta(days=15, hours=1),
    #     )

    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=30),
    #         end_at=today_event_time - timedelta(days=30) + timedelta(hours=1),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=30),
    #         end_at=today_event_time + timedelta(days=30, hours=1),
    #     )

    #     # event that starts within range but ends outside (1 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=15),
    #     )

    #     # event that starts outside range but ends inside (2 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time - timedelta(days=7),
    #     )
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time + timedelta(days=7),
    #         end_at=today_event_time + timedelta(days=8),
    #     )

    #     # event that starts outside range and ends outside range (1 valid)
    #     create_test_event(
    #         host=club,
    #         start_at=today_event_time - timedelta(days=15),
    #         end_at=today_event_time + timedelta(days=15),
    #     )

    #     url = event_list_url(end_at=today + mod_shift)
    #     res = self.client.get(url)

    #     self.assertResOk(res)
    #     data = res.json()["results"]

    #     self.assertEqual(len(data), events_in_range)

    def test_get_both_filters(self):
        """Should get events from one week ago to one week into the future"""
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_event_time = today.replace(hour=12)
        timedelta(days=14)
        mod_shift = timedelta(days=7)

        events_in_range = 8

        # Create test club
        club = create_test_club(members=[self.user])

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
        data = res.json()["results"]

        self.assertEqual(len(data), events_in_range)

    def test_create_event_poll(self):
        """Should create a new event and it's poll."""

        club = create_test_club(admins=[self.user])

        payload = {
            "start_at": "2025-10-22T13:00:00Z",
            "end_at": "2025-10-22T15:00:00Z",
            "name": "Test Event",
            "hosts": [{"club_id": club.id, "is_primary": True}],
            "enable_attendance": True,
        }

        url = event_list_url()
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        # Check database event
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertIsNotNone(event.poll)

    def test_delete_event_poll_disables_attendance(self):
        """Should disable event attendance when poll is deleted."""

        club = create_test_club(admins=[self.user])
        event: Event = create_test_event(host=club, enable_attendance=True)
        poll = event.poll

        self.assertTrue(event.enable_attendance)

        url = polls_detail_url(poll.pk)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204, res.content)

        # Refresh event from database
        event.refresh_from_db()
        self.assertFalse(event.enable_attendance)

    @freezegun.freeze_time("12/30/25 13:00:00")
    def test_get_event_heatmap(self):
        """Should return dict mapping each day to a count of events."""

        # Test: Day with multiple events
        c1 = create_test_club(members=[self.user])  # 3 events
        # Test: Heatmap for multiple clubs
        c2 = create_test_club(members=[self.user])  # 1 event
        # Test: Exclude other club events
        c3 = create_test_club()  # 2 events
        # Test: Only include selected clubs
        c4 = create_test_club(members=[self.user])  # 0 events

        # 12/15 - 1 event (c1)
        create_test_event(
            host=c1, start_at="12/15/25 17:00:00", end_at="12/15/25 19:00:00"
        )

        # 12/17 - 2 events (c1)
        create_test_event(
            host=c1, start_at="12/17/25 09:00:00", end_at="12/17/25 11:00:00"
        )
        create_test_event(
            host=c1, start_at="12/17/25 17:00:00", end_at="12/17/25 19:00:00"
        )

        # 12/18 - 1 event (c2)
        create_test_event(
            host=c2, start_at="12/18/25 17:00:00", end_at="12/18/25 19:00:00"
        )

        # 12/18 - 1 event (c3)
        create_test_event(
            host=c3, start_at="12/18/25 17:00:00", end_at="12/18/25 19:00:00"
        )

        # 12/19 - 1 event (c3)
        create_test_event(
            host=c3, start_at="12/19/25 17:00:00", end_at="12/19/25 19:00:00"
        )

        # Heatmap for all clubs
        url = reverse_query("api-events:heatmap")
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        self.assertEqual(data["total_events"], 4)
        self.assertEqual(data["start_date"], "2025-10-01")
        self.assertEqual(data["end_date"], "2026-02-28")

        h0 = data["heatmap"]

        self.assertIn("2025-12-15", h0.keys())
        self.assertIn("2025-12-17", h0.keys())
        self.assertIn("2025-12-18", h0.keys())
        self.assertIn("2025-12-19", h0.keys())

        for date, count in h0.items():
            if date == "2025-12-15":
                self.assertEqual(count, 1)
            elif date == "2025-12-17":
                self.assertEqual(count, 2)
            elif date == "2025-12-18":
                self.assertEqual(count, 1)
            else:
                self.assertEqual(count, 0)

        # Heatmap for clubs 1 and 2
        url = reverse_query("api-events:heatmap", query={"clubs": [c1.pk, c2.pk]})
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        self.assertEqual(data["total_events"], 4)

        # Heatmap for club 4
        url = reverse_query("api-events:heatmap", query={"clubs": [c4.pk]})
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        self.assertEqual(data["total_events"], 0)

        h4 = data["heatmap"]
        for _, count in h4.items():
            self.assertEqual(count, 0)

        # Heatmap for all clubs, outside date range
        url = reverse_query(
            "api-events:heatmap",
            query={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        )
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        self.assertEqual(data["start_date"], "2025-01-01")
        self.assertEqual(data["end_date"], "2025-01-31")
        self.assertEqual(data["total_events"], 0)

        h0 = data["heatmap"]
        for _, count in h4.items():
            self.assertEqual(count, 0)
