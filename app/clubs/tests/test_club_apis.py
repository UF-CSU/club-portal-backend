"""
Unit tests focused around REST APIs for the Clubs Service.
"""

from typing import Optional

from django.urls import reverse
from rest_framework.test import APIClient

from clubs.models import ClubApiKey
from clubs.tests.utils import create_test_club
from core.abstracts.tests import ApiTestsBase, AuthApiTestsBase, EmailTestsBase
from lib.faker import fake
from users.models import User
from users.tests.utils import create_test_user


def club_invite_url(club_id: int):
    return reverse("api-clubs:invite", args=[club_id])


def club_members_list_url(club_id: Optional[int] = None):
    return reverse("api-clubs:clubmember-list", args=[club_id])


def club_detail_url(club_id: int):
    return reverse("api-clubs:club-detail", args=[club_id])


def club_apikey_list_url(club_id: int):
    return reverse("api-clubs:apikey-list", args=[club_id])


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

    def test_using_apikey(self):
        """A request should be able to be made using an API Key."""

        club = create_test_club()

        key = ClubApiKey.objects.create(
            club=club,
            name="Test Key",
            permissions=["clubs.view_club", "clubs.view_clubmembership"],
        )

        self.client = APIClient()
        self.client.force_authenticate(user=key.user_agent)

        url = club_detail_url(club.id)
        res = self.client.get(url)
        self.assertResOk(res)

        # Check permission denied for other club
        club2 = create_test_club()

        url2 = club_detail_url(club2.id)
        res = self.client.get(url2)
        self.assertResForbidden(res)


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
        """Should be able to create club member without sending emails, will create user."""

        # Initial setup
        club = create_test_club()
        mem_email = fake.safe_email()
        payload = {
            "club_id": club.id,
            "user": {"email": mem_email, "send_account_email": False},
            "send_email": False,
            "is_owner": False,
            "redirect_to": fake.url(),
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
            "redirect_to": fake.url(),
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
            "redirect_to": fake.url(),
        }

        # Check initial state
        self.assertEqual(User.objects.filter(email=mem_email).count(), 0)

        # Api request
        url = club_members_list_url(club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(2)  # Emails: club invite, setup account
        self.assertEqual(User.objects.filter(email=mem_email).count(), 1)

        user = User.objects.filter(email=mem_email).first()
        self.assertEqual(
            user.has_usable_password(),
            False,
            f"User {user} as a password (hash): {user.password}",
        )
        self.assertEqual(user.club_memberships.count(), 1)

    def test_create_club_api_key(self):
        """Should be able to create an api key for a club."""

        club = create_test_club()
        url = club_apikey_list_url(club.id)

        payload = {
            "name": "Test Key",
            "description": "Lorem ipsum dolor sit amet.",
            "permissions": [
                "clubs.view_club",
                "clubs.view_clubmembership",
            ],
        }
        res = self.client.post(url, payload)
        self.assertResCreated(res)
        res_body = res.json()

        self.assertEqual(ClubApiKey.objects.count(), 1)
        key = ClubApiKey.objects.first()

        self.assertEqual(res_body["secret"], key.get_secret())
