"""
Unit tests focused around REST APIs for the Clubs Service.
"""

from typing import Optional

from clubs.tests.utils import create_test_club
from core.abstracts.tests import ApiTestsBase, AuthApiTestsBase, EmailTestsBase
from django.urls import reverse
from lib.faker import fake
from users.models import User
from users.tests.utils import create_test_user


def club_invite_url(club_id: int):
    return reverse("api-clubs:invite", args=[club_id])


def club_members_list_url(club_id: Optional[int] = None):
    return reverse("api-clubs:club-members-list", args=[club_id])


class ClubsApiPublicTests(ApiTestsBase):
    """Tests for public routes on clubs api."""

    def test_invite_login_required(self):
        """An unauthenticated user should get an error when trying to send invites."""

        email_count = 5

        club = create_test_club()
        url = club_invite_url(club.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload)
        self.assertResUnauthorized(res)


class ClubsApiPrivateTests(AuthApiTestsBase, EmailTestsBase):
    """Tests for club api routes."""

    def test_send_email_invites_api(self):
        """Should be able to send email invites via the API."""

        email_count = 5

        club = create_test_club()
        url = club_invite_url(club.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload)
        self.assertResAccepted(res)
        self.assertEmailsSent(email_count)

    def test_create_club_member_new_user(self):
        """Should be able to create club member without sending email, will create user."""

        # Initial setup
        club = create_test_club()
        mem_email = fake.safe_email()
        payload = {
            "club_id": club.id,
            "user": {"email": mem_email},
            "send_email": False,
            "is_owner": False,
        }

        # Check initial state
        self.assertEqual(User.objects.filter(email=mem_email).count(), 0)

        # Api request
        url = club_members_list_url(club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(0)
        self.assertEqual(User.objects.filter(email=mem_email).count(), 1)

        user = User.objects.filter(email=mem_email).first()
        self.assertEqual(
            user.has_usable_password(),
            False,
            f"User {user} has a password",
        )
        self.assertEqual(user.club_memberships.count(), 1)

    def test_create_club_member_existing_user(self):
        """Should be able to create club member without sending email, use existing user."""

        # Initial setup
        club = create_test_club()
        user = create_test_user()
        payload = {
            "club_id": club.id,
            "user": {"email": user.email},
            "send_email": False,
            "is_owner": False,
        }

        # Check initial state
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(user.club_memberships.count(), 0)

        # Api request
        url = club_members_list_url(club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(0)
        self.assertEqual(User.objects.count(), 2)

        user.refresh_from_db()
        self.assertEqual(user.club_memberships.count(), 1)

    def test_invite_club_admin(self):
        """Should be able to send an email invite to a new club admin."""

        # Initial setup
        club = create_test_club()
        mem_email = fake.safe_email()
        payload = {
            "club_id": club.id,
            "user": {"email": mem_email},
            "is_owner": True,
            "send_email": True,
        }

        # Check initial state
        self.assertEqual(User.objects.filter(email=mem_email).count(), 0)

        # Api request
        url = club_members_list_url(club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(1)
        self.assertEqual(User.objects.filter(email=mem_email).count(), 1)

        user = User.objects.filter(email=mem_email).first()
        self.assertEqual(
            user.has_usable_password(),
            False,
            f"User {user} as a password (hash): {user.password}",
        )
        self.assertEqual(user.club_memberships.count(), 1)
