"""
Unit tests for Club business logic.
"""

from core.abstracts.tests import EmailTestsBase, TestsBase
from django.core import exceptions
from lib.faker import fake
from users.tests.utils import create_test_user

from clubs.models import Club
from clubs.services import ClubService
from clubs.tests.utils import create_test_club, join_club_url


class ClubServiceLogicTests(TestsBase):
    """Test club business logic not covered in views."""

    model = Club

    def setUp(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)

        return super().setUp()

    def test_join_link(self):
        """Join link should be correct."""

        link = self.service.join_url
        self.assertEqual(link, join_club_url(self.club.id))

    def test_memberships(self):
        """Should manage relationships between clubs and users."""

        user = create_test_user()
        with self.assertRaises(exceptions.BadRequest):
            self.service.increase_member_points(user, 1)

        mem = self.service.add_member(user)
        self.assertEqual(self.club.memberships.count(), 1)
        self.assertEqual(mem.points, 0)

        self.service.increase_member_points(user, 1)
        mem.refresh_from_db()
        self.assertEqual(mem.points, 1)

        self.service.increase_member_points(user, 5)
        mem.refresh_from_db()
        self.assertEqual(mem.points, 6)

        self.service.decrease_member_points(user, 1)
        mem.refresh_from_db()
        self.assertEqual(mem.points, 5)

        with self.assertRaises(exceptions.BadRequest):
            self.service.decrease_member_points(user, 6)
        mem.refresh_from_db()
        self.assertEqual(mem.points, 5)


class ClubEmailTests(EmailTestsBase):
    """Test emails that are sent in connection to clubs."""

    def setUp(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)
        return super().setUp()

    def test_club_invite(self):
        """Club email invite should send, link should work."""
        email_count = 5
        emails = [fake.safe_email() for _ in range(email_count)]

        self.service.send_email_invite(emails)
        self.assertEmailsSent(email_count)

        # URL functionality is tested in test_club_views.py
        self.assertInEmailBodies(self.service.full_join_url)
