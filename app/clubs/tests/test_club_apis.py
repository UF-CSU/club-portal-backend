"""
Unit tests focused around REST APIs for the Clubs Service.
"""

from django.urls import reverse

from clubs.tests.utils import create_test_club
from core.abstracts.tests import ApiTestsBase, AuthApiTestsBase, EmailTestsBase
from lib.faker import fake


def get_club_invite_url(club_id: int):
    return reverse("api-clubs:invite", args=[club_id])


class ClubsApiPublicTests(ApiTestsBase):
    """Tests for public routes on clubs api."""

    def test_invite_login_required(self):
        """An unauthenticated user should get an error when trying to send invites."""

        email_count = 5

        club = create_test_club()
        url = get_club_invite_url(club.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload)
        self.assertResUnauthorized(res)


class ClubsApiPrivateTests(AuthApiTestsBase, EmailTestsBase):
    """Tests for club api routes."""

    def test_send_email_invites_api(self):
        """Should be able to send email invites via the API."""

        email_count = 5

        club = create_test_club()
        url = get_club_invite_url(club.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload)
        self.assertResAccepted(res)
        self.assertEmailsSent(email_count)
