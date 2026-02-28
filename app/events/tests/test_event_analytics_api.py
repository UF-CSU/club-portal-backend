from datetime import date, datetime, time

import factory
import freezegun
from analytics.models import QRCode
from clubs.models import Club, ClubFile
from clubs.services import ClubService
from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import override_settings
from rest_framework.response import Response
from users.models import Profile, User
from users.tests.utils import create_test_user

from events.models import DayType, Event, EventType, RecurringEvent
from events.services import EventAnalytics, RecurringEventService
from events.tests.utils import (
    EVENT_LIST_URL,
    create_test_attendance,
    create_test_event,
    event_detail_url,
)


class EventAnalyticsTestsBase(PrivateApiTestsBase):
    """Base utilities for event analytics."""

    def assertEventAnalytics(
        self, res: Response, data: EventAnalytics, assert_empty=False
    ):
        """
        Check the analytics data in an event response.

        *NOTE: Can exclude the diff values, will be calculated in assertion.*
        """

        analytics = res.json()["analytics"]

        if assert_empty:
            # Ensure no analytics were supplied
            self.assertIsNone(analytics)
            return

        # Verify event analytics
        self.assertNumsEqual(analytics["users_total"], data.event_users_total)
        self.assertNumsEqual(analytics["members_total"], data.event_members_total)
        self.assertNumsEqual(analytics["returning_total"], data.event_returning_total)

        # Previous event analytics
        self.assertEqual(analytics["previous_event"]["id"], data.prev_id)
        self.assertNumsEqual(
            analytics["previous_event"]["users_total"], data.prev_users_total
        )
        self.assertNumsEqual(
            analytics["previous_event"]["users_diff"],
            data.event_users_total - data.prev_users_total,
        )
        self.assertNumsEqual(
            analytics["previous_event"]["members_total"], data.prev_members_total
        )
        self.assertNumsEqual(
            analytics["previous_event"]["members_diff"],
            data.event_members_total - data.prev_members_total,
        )
        self.assertNumsEqual(
            analytics["previous_event"]["returning_total"], data.prev_returning_total
        )
        self.assertNumsEqual(
            analytics["previous_event"]["returning_diff"],
            data.event_returning_total - data.prev_returning_total,
        )

        # Event type analytics
        self.assertNumsEqual(
            analytics["event_type"]["events_count"], data.evtype_events_count
        )
        self.assertNumsEqual(
            analytics["event_type"]["users_avg"], data.evtype_users_avg
        )
        self.assertNumsEqual(
            analytics["event_type"]["users_diff"],
            data.event_users_total - data.evtype_users_avg,
        )
        self.assertNumsEqual(
            analytics["event_type"]["members_avg"], data.evtype_members_avg
        )
        self.assertNumsEqual(
            analytics["event_type"]["members_diff"],
            data.event_users_total - data.evtype_members_avg,
        )
        self.assertNumsEqual(
            analytics["event_type"]["returning_avg"], data.evtype_returning_avg
        )
        self.assertNumsEqual(
            analytics["event_type"]["returning_diff"],
            data.event_returning_total - data.evtype_returning_avg,
        )

        # Recurring event analytics
        self.assertNumsEqual(
            analytics["recurring_event"]["events_count"], data.rec_events_count
        )
        self.assertNumsEqual(
            analytics["recurring_event"]["users_avg"], data.rec_users_avg
        )
        self.assertNumsEqual(
            analytics["recurring_event"]["users_diff"],
            data.event_users_total - data.rec_users_avg,
        )
        self.assertNumsEqual(
            analytics["recurring_event"]["members_avg"], data.rec_members_avg
        )
        self.assertNumsEqual(
            analytics["recurring_event"]["members_diff"],
            data.event_members_total - data.rec_members_avg,
        )
        self.assertNumsEqual(
            analytics["recurring_event"]["returning_avg"], data.rec_returning_avg
        )
        self.assertNumsEqual(
            analytics["recurring_event"]["returning_diff"],
            data.event_returning_total - data.rec_returning_avg,
        )


class EventBasicAnalyticsApiTests(EventAnalyticsTestsBase):
    """Unit tests for events api specifically for analytics."""

    def setUp(self):
        super().setUp()
        self.club = create_test_club(admins=[self.user])

    def test_analytics_not_in_list(self):
        """Should not show analytics in"""

        create_test_event(host=self.club)
        url = EVENT_LIST_URL
        res = self.client.get(url)
        self.assertResOk(res)

        # Verify analytics not in event obj in list
        data = res.json()["results"]
        self.assertEqual(len(data), 1)
        data = data[0]

        self.assertNotIn("analytics", data.keys())

    def test_default_analytics_in_details(self):
        """Should show analytics field in event details."""

        event = create_test_event(host=self.club)
        url = event_detail_url(event.pk)
        res = self.client.get(url)
        self.assertResOk(res)

        # Verify analytics in event detail object
        data = res.json()
        self.assertIn("analytics", data.keys())

        # Verify analytics for unattended event, all default values
        self.assertEventAnalytics(res, EventAnalytics(event.pk), assert_empty=True)


class EventAnalyticsApiCalculationTests(EventAnalyticsTestsBase):
    """Unit tests for Event Analytics API."""

    LOAD_CACHED_DATA = True

    @factory.django.mute_signals(post_save)
    def import_cached_data(self):
        call_command("loaddata", "fixtures/event-analytics-test-data.json")

    @override_settings(ENABLE_AUTO_CREATE_CLUB_LOGO=False)
    def setUp(self):
        """
        Dataset
        ------------

        Clubs: 2
        - CSU
        - OSC

        Users: 200 (###-user@example.com, 0-199)
        - [0-5]: Executive Member of CSU
        - [0-14]: Member of CSU
        - [15-79]: Guest of CSU
        - [80-99]: Member of CSU
        - [100-104]: Executive Member of OSC
        - [105-107]: Member of OSC
        - [108-179]: Guest of OSC
        - [180-189]: Executive Member of OSC

        Calendar
        ------------

        CSU GBMs:
        - 1/5: 80 users, 18 members, 0 returning
        - 2/17: 50 users, 15 members, 40 returning

        CSU Dev Meetings:
        - [0] 1/12: 15 users, 15 members, 10 returning (10 attended GBM)
        - [1] 1/14: 20 users, 20 members, 15 returning
        - [2] 1/19: 18 users, 18 members, 18 returning
        - [3] 1/21: 15 users, 15 members, 15 returning
        - [4] 1/26: 16 users, 16 members, 16 returning
        - [5] 1/28: 15 users, 15 members, 15 returning
        - [6] 2/02: 14 users, 14 members, 14 returning
        - [7] 2/04: 13 users, 13 members, 13 returning
        - [8] 2/09: 12 users, 12 members, 12 returning
        - [9] 2/11: 13 users, 13 members, 13 returning
        - [10] 2/16: 12 users, 12 members, 12 returning
        - [11] 2/18: 10 users, 10 members, 10 returning

        CSU Exec Meetings:
        - [0] 1/16: 5 users, 5 members, 5 returning (all 5 attended previous meetings)
        - [1] 1/23: 6 users, 6 members, 5 returning
        - [2] 1/30: 4 users, 4 members, 4 returning
        - [3] 2/06: 5 users, 5 members, 5 returning
        - [4] 2/13: 5 users, 5 members, 5 returning
        - [5] 2/20: 4 users, 4 members, 4 returning

        OSC GBMs:
        - 1/12: 80 users, 8 members, 0 returning

        OSC Casual Coding:
        - [0] 1/13: 75 users, 10 members, (65 guests), 0 returning
        - [1] 1/15: 80 users, 8 members, (72 guests), 65 returning
        - [2] 1/20: 78 users, 9 members, (69 guests), 70 returning
        - [3] 1/22: 50 users, 10 members, (40 guests), 50 returning
        - [4] 1/27: 43 users, 7 members, (36 guests), 40 returning
        - [5] 1/29: 32 users, 10 members, (22 guests), 32 returning
        - [6] 2/03: 35 users, 9 members, (26 guests), 30 returning
        - [7] 2/05: 30 users, 9 members, (21 guests), 29 returning
        - [8] 2/10: 28 users, 10 members, (18 guests), 28 returning
        - [9] 2/12: 30 users, 8 members, (22 guests), 25 returning
        - [10] 2/17: 25 users, 9 members, (16 guests), 20 returning
        - [11] 2/19: 20 users, 7 members, (13 guests), 15 returning

        OSC Exec Meetings:
        - [0] 1/14: 10 users, 10 members, 0 returning
        - [1] 1/21: 12 users, 12 members, 10 returning
        - [2] 1/28: 8 users, 8 members, 8 returning
        - [3] 2/04: 10 users, 10 members, 9 returning
        - [4] 2/11: 10 users, 10 members, 10 returning
        - [5] 2/18: 8 users, 8 members, 8 returning
        """
        super().setUp()

        if self.LOAD_CACHED_DATA:
            self.import_cached_data()
            self.club = Club.objects.get(id=1)
            self.csu = self.club
            self.osc = Club.objects.get(id=2)
            self.csu_gbm_1 = Event.objects.get(name="CSU GBM 1")
            self.csu_gbm_2 = Event.objects.get(name="CSU GBM 2")

            csu_dev_meetings_rec = RecurringEvent.objects.get(
                name="CSU Weekly Dev Meeting"
            )
            self.csu_dev_meetings = csu_dev_meetings_rec.events.all().order_by(
                "start_at"
            )
            csu_exec_meetings_rec = RecurringEvent.objects.get(
                name="CSU Weekly Exec Meeting"
            )
            self.csu_exec_meetings = csu_exec_meetings_rec.events.all().order_by(
                "start_at"
            )

        else:
            # Club & User data
            # ------------------------

            # Clubs
            self.club = create_test_club(
                name="Computing Student Union", alias="CSU", admins=[self.user]
            )
            self.csu = self.club
            csu_svc = ClubService(self.csu)

            self.osc = create_test_club(name="Open Source Club", alias="OSC")
            osc_svc = ClubService(self.osc)

            ClubFile.objects.all().delete()

            # CSU events
            self.csu_gbm_1 = create_test_event(
                host=self.csu,
                name="CSU GBM 1",
                event_type=EventType.GBM,
                start_at=datetime(2026, 1, 5, 18, 0, 0),
                end_at=datetime(2026, 1, 5, 20, 0, 0),
                enable_attendance=True,
            )

            self.csu_gbm_2 = create_test_event(
                host=self.csu,
                name="CSU GBM 2",
                event_type=EventType.GBM,
                start_at=datetime(2026, 2, 17, 18, 0, 0),
                end_at=datetime(2026, 2, 17, 20, 0, 0),
                enable_attendance=True,
            )

            csu_dev_meetings_rec = RecurringEvent.objects.create(
                "CSU Weekly Dev Meeting",
                club=self.csu,
                days=[DayType.MONDAY, DayType.WEDNESDAY],
                start_date=date(2026, 1, 11),
                end_date=date(2026, 5, 10),
                event_start_time=time(hour=18),
                event_end_time=time(hour=20),
                event_type=EventType.INTERNAL_MEETING,
                enable_attendance=True,
            )
            self.csu_dev_meetings = (
                RecurringEventService(csu_dev_meetings_rec)
                .sync_events()
                .order_by("start_at")
            )

            csu_exec_meetings_rec = RecurringEvent.objects.create(
                "CSU Weekly Exec Meeting",
                club=self.csu,
                days=[DayType.FRIDAY],
                start_date=date(2026, 1, 11),
                end_date=date(2026, 5, 10),
                event_start_time=time(hour=16),
                event_end_time=time(hour=17),
                event_type=EventType.INTERNAL_MEETING,
                enable_attendance=True,
            )
            self.csu_exec_meetings = (
                RecurringEventService(csu_exec_meetings_rec)
                .sync_events()
                .order_by("start_at")
            )

            # OSC events
            self.osc_gbm_1 = create_test_event(
                host=self.osc,
                name="OSC GBM 1",
                event_type=EventType.GBM,
                start_at=datetime(2026, 1, 12, 18, 0, 0),
                end_at=datetime(2026, 1, 12, 20, 0, 0),
                enable_attendance=True,
            )

            osc_ccs_rec = RecurringEvent.objects.create(
                "Casual Coding",
                club=self.osc,
                days=[DayType.TUESDAY, DayType.THURSDAY],
                start_date=date(2026, 1, 11),
                end_date=date(2026, 5, 10),
                event_start_time=time(hour=17),
                event_end_time=time(hour=19),
                event_type=EventType.SOCIAL,
                enable_attendance=True,
            )
            self.osc_ccs = (
                RecurringEventService(osc_ccs_rec).sync_events().order_by("start_at")
            )

            osc_exec_meetings_rec = RecurringEvent.objects.create(
                "OSC Weekly Exec Meeting",
                club=self.osc,
                days=[DayType.WEDNESDAY],
                start_date=date(2026, 1, 11),
                end_date=date(2026, 5, 10),
                event_start_time=time(hour=16),
                event_end_time=time(hour=17),
                event_type=EventType.INTERNAL_MEETING,
                enable_attendance=True,
            )
            self.osc_exec_meetings = (
                RecurringEventService(osc_exec_meetings_rec)
                .sync_events()
                .order_by("start_at")
            )

            # Users
            users = []
            for i in range(200):
                user = create_test_user(email=f"{i}-user@example.com")
                user.profile.image = None
                user.profile.save()
                users.append(user)

            # CSU GBMS
            # ------------------------

            # Attended CSU GBM 1 & 2
            for i, user in enumerate(users[0:40]):
                if i < 15:
                    csu_svc.add_member(user)

                create_test_attendance(self.csu_gbm_1, user)
                create_test_attendance(self.csu_gbm_2, user)

            # Just attended CSU GBM 1
            for i, user in enumerate(users[40:70]):
                if i < 43:
                    csu_svc.add_member(user)

                create_test_attendance(self.csu_gbm_1, user)

            # Just attended CSU GBM 2
            for user in users[70:80]:
                create_test_attendance(self.csu_gbm_2, user)

            # CSU Dev Meetings
            # ------------------------

            # From GBM, Attended all meetings
            for user in users[0:10]:
                for event in self.csu_dev_meetings:
                    create_test_attendance(event, user)

            # Each meeting
            for i, user in enumerate(users[80:100]):
                csu_svc.add_member(user)

                if i < 2:  # Events with 12+ members
                    create_test_attendance(self.csu_dev_meetings[0], user)
                    create_test_attendance(self.csu_dev_meetings[1], user)
                    create_test_attendance(self.csu_dev_meetings[2], user)
                    create_test_attendance(self.csu_dev_meetings[3], user)
                    create_test_attendance(self.csu_dev_meetings[4], user)
                    create_test_attendance(self.csu_dev_meetings[5], user)
                    create_test_attendance(self.csu_dev_meetings[6], user)
                    create_test_attendance(self.csu_dev_meetings[7], user)
                    create_test_attendance(self.csu_dev_meetings[8], user)
                    create_test_attendance(self.csu_dev_meetings[9], user)
                    create_test_attendance(self.csu_dev_meetings[10], user)
                elif i < 3:  # Events with 13+ members
                    create_test_attendance(self.csu_dev_meetings[0], user)
                    create_test_attendance(self.csu_dev_meetings[1], user)
                    create_test_attendance(self.csu_dev_meetings[2], user)
                    create_test_attendance(self.csu_dev_meetings[3], user)
                    create_test_attendance(self.csu_dev_meetings[4], user)
                    create_test_attendance(self.csu_dev_meetings[5], user)
                    create_test_attendance(self.csu_dev_meetings[6], user)
                    create_test_attendance(self.csu_dev_meetings[7], user)
                    create_test_attendance(self.csu_dev_meetings[9], user)
                elif i < 4:  # Events with 14+ members
                    create_test_attendance(self.csu_dev_meetings[0], user)
                    create_test_attendance(self.csu_dev_meetings[1], user)
                    create_test_attendance(self.csu_dev_meetings[2], user)
                    create_test_attendance(self.csu_dev_meetings[3], user)
                    create_test_attendance(self.csu_dev_meetings[4], user)
                    create_test_attendance(self.csu_dev_meetings[5], user)
                    create_test_attendance(self.csu_dev_meetings[6], user)
                elif i < 5:  # Events with 15+ members
                    create_test_attendance(self.csu_dev_meetings[0], user)
                    create_test_attendance(self.csu_dev_meetings[1], user)
                    create_test_attendance(self.csu_dev_meetings[2], user)
                    create_test_attendance(self.csu_dev_meetings[3], user)
                    create_test_attendance(self.csu_dev_meetings[4], user)
                    create_test_attendance(self.csu_dev_meetings[5], user)
                elif i < 6:  # Events with 16+ members
                    create_test_attendance(self.csu_dev_meetings[1], user)
                    create_test_attendance(self.csu_dev_meetings[2], user)
                    create_test_attendance(self.csu_dev_meetings[4], user)
                elif i < 8:  # Events with 18+ members
                    create_test_attendance(self.csu_dev_meetings[1], user)
                    create_test_attendance(self.csu_dev_meetings[2], user)
                elif i < 10:  # Events with 20+ members
                    create_test_attendance(self.csu_dev_meetings[1], user)

            # CSU Exec Meetings
            # ------------------------

            for i, user in enumerate(users[0:6]):
                if i < 4:  # Events with 4+ members
                    create_test_attendance(self.csu_exec_meetings[0], user)
                    create_test_attendance(self.csu_exec_meetings[1], user)
                    create_test_attendance(self.csu_exec_meetings[2], user)
                    create_test_attendance(self.csu_exec_meetings[3], user)
                    create_test_attendance(self.csu_exec_meetings[4], user)
                    create_test_attendance(self.csu_exec_meetings[5], user)
                elif i < 5:  # Events with 5+ members
                    create_test_attendance(self.csu_exec_meetings[0], user)
                    create_test_attendance(self.csu_exec_meetings[1], user)
                    create_test_attendance(self.csu_exec_meetings[3], user)
                    create_test_attendance(self.csu_exec_meetings[4], user)
                elif i < 6:  # Events with 6+ members
                    create_test_attendance(self.csu_exec_meetings[1], user)

            # OSC GBM
            # ------------------------

            for i, user in enumerate(users[100:180]):
                if i < 8:
                    osc_svc.add_member(user)

                create_test_attendance(self.osc_gbm_1, user)

            # OSC Casual Coding
            # ------------------------

            # Members that attended events

            for i, user in enumerate(users[100:108]):
                if i < 7:  # Events with 7+ members
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[8], user)
                    create_test_attendance(self.osc_ccs[9], user)
                    create_test_attendance(self.osc_ccs[10], user)
                    create_test_attendance(self.osc_ccs[11], user)
                elif i < 8:  # Events with 8+ members
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[8], user)
                    create_test_attendance(self.osc_ccs[9], user)
                    create_test_attendance(self.osc_ccs[10], user)

            for i, user in enumerate(
                users[180:190]
            ):  # Add memberships to 10 additional people
                osc_svc.add_member(user)

                if i < 1:  # Events with 9+ members
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[8], user)
                    create_test_attendance(self.osc_ccs[10], user)
                elif i < 2:  # Events with 10+ members
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[8], user)

            # Guests that attended events
            for i, user in enumerate(users[108:180]):  # <= 72 guests
                if i < 13:  # Events with 13+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[8], user)
                    create_test_attendance(self.osc_ccs[9], user)
                    create_test_attendance(self.osc_ccs[10], user)
                    create_test_attendance(self.osc_ccs[11], user)
                elif i < 16:  # Events with 16+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[8], user)
                    create_test_attendance(self.osc_ccs[9], user)
                    create_test_attendance(self.osc_ccs[10], user)
                elif i < 18:  # Events with 18+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[8], user)
                    create_test_attendance(self.osc_ccs[9], user)
                elif i < 21:  # Events with 21+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[7], user)
                    create_test_attendance(self.osc_ccs[9], user)
                elif i < 22:  # Events with 22+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[5], user)
                    create_test_attendance(self.osc_ccs[6], user)
                    create_test_attendance(self.osc_ccs[9], user)
                elif i < 26:  # Events with 26+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                    create_test_attendance(self.osc_ccs[6], user)
                elif i < 36:  # Events with 36+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                    create_test_attendance(self.osc_ccs[4], user)
                elif i < 40:  # Events with 40+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                    create_test_attendance(self.osc_ccs[3], user)
                elif i < 65:  # Events with 65+ guests
                    create_test_attendance(self.osc_ccs[0], user)
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                elif i < 69:  # Events with 69+ guests
                    create_test_attendance(self.osc_ccs[1], user)
                    create_test_attendance(self.osc_ccs[2], user)
                elif i < 72:  # Events with 72+ guests
                    create_test_attendance(self.osc_ccs[1], user)

            # OSC Exec Meetings
            # ------------------------

            for user in users[100:105]:  # 5 of the first 8 members are execs
                create_test_attendance(self.osc_exec_meetings[0], user)
                create_test_attendance(self.osc_exec_meetings[1], user)
                create_test_attendance(self.osc_exec_meetings[2], user)
                create_test_attendance(self.osc_exec_meetings[3], user)
                create_test_attendance(self.osc_exec_meetings[4], user)
                create_test_attendance(self.osc_exec_meetings[5], user)

            for i, user in enumerate(users[180:190]):  # <= 15 members
                if i < 3:  # Events with 8+ members
                    create_test_attendance(self.osc_exec_meetings[0], user)
                    create_test_attendance(self.osc_exec_meetings[1], user)
                    create_test_attendance(self.osc_exec_meetings[2], user)
                    create_test_attendance(self.osc_exec_meetings[3], user)
                    create_test_attendance(self.osc_exec_meetings[4], user)
                    create_test_attendance(self.osc_exec_meetings[5], user)
                elif i < 5:  # Events with 10+ members
                    create_test_attendance(self.osc_exec_meetings[0], user)
                    create_test_attendance(self.osc_exec_meetings[1], user)
                    create_test_attendance(self.osc_exec_meetings[3], user)
                    create_test_attendance(self.osc_exec_meetings[4], user)
                elif i < 7:  # Events with 12+ members
                    create_test_attendance(self.osc_exec_meetings[1], user)

            QRCode.objects.all().delete()
            Profile.objects.all().update(image=None)

            call_command(
                "dumpdata",
                "--indent",
                "2",
                # Exclude django meta data
                "--exclude",
                "auth.permission",
                "--exclude",
                "contenttypes",
                output="fixtures/event-analytics-test-data.json",
            )

    @freezegun.freeze_time("02/21/2026 13:00:00")
    def test_event_average_analytics(self):
        """Should be able to calculate event analytics for previous event, event type, and recurring event."""

        event = self.csu_dev_meetings[2]

        # Expected analytics from test data
        expected_analytics = EventAnalytics(
            # Event analytics
            event_id=event.pk,
            event_users_total=18,
            event_members_total=18,
            event_returning_total=18,
            # Previous event
            prev_id=self.csu_dev_meetings[1].pk,
            prev_users_total=20,
            prev_members_total=20,
            prev_returning_total=15,
            # Event type
            evtype=event.event_type,
            evtype_events_count=2 + 1,
            evtype_users_avg=(15 + 20 + 5) / 3,
            evtype_members_avg=(15 + 20 + 5) / 3,
            evtype_returning_avg=(10 + 15 + 5) / 3,
            # Recurring event
            rec_events_count=2,
            rec_users_avg=(15 + 20) / 2,
            rec_members_avg=(15 + 20) / 2,
            rec_returning_avg=(10 + 15) / 2,
        )

        # Verify test data
        # users_count = event.poll.submissions.all().distinct('user_id').count()
        # self.assertEqual(users_count, 18)
        # members_count =
        prev_event = self.csu_dev_meetings[1]
        club_mem_ids = User.objects.filter(clubs__id=self.csu.pk)
        prev_event_users_total = prev_event.poll.submissions.count()
        prev_event_members_total = prev_event.poll.submissions.filter(
            user_id__in=club_mem_ids
        ).count()
        prev_submission_users = (
            User.objects.filter(poll_submissions__poll__club_id=self.csu.pk)
            .filter(poll_submissions__poll__event__start_at__lt=prev_event.start_at)
            .values_list("id", flat=True)
        )
        prev_event_returning_total = prev_event.poll.submissions.filter(
            user_id__in=prev_submission_users
        ).count()
        self.assertNumsEqual(
            prev_event_users_total, expected_analytics.prev_users_total
        )
        self.assertNumsEqual(
            prev_event_members_total, expected_analytics.prev_members_total
        )
        self.assertNumsEqual(
            prev_event_returning_total, expected_analytics.prev_returning_total
        )

        # Verify api response
        url = event_detail_url(event_id=event.pk)
        res = self.client.get(url)
        self.assertEventAnalytics(res, expected_analytics)
