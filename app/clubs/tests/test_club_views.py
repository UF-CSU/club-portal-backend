from django.contrib.auth import get_user_model
from rest_framework import status

from clubs.models import ClubMembership
from clubs.services import ClubService
from clubs.tests.utils import club_home_url, create_test_club, join_club_url
from core.abstracts.tests import ViewTestsBase
from users.tests.utils import create_test_user, login_user_url, register_user_url

User = get_user_model()


class ClubViewTests(ViewTestsBase):
    """Unit tests for club views."""

    def setUp(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)

        return super().setUp()

    def test_join_club_view_guest_login(self):
        """Should redirect to register page with query param."""

        url = join_club_url(self.club.id)
        redirect_url = f"{login_user_url()}?next={url}"
        res = self.client.get(url)

        # Check guest redirects to login
        self.assertRedirects(
            res, expected_url=redirect_url, status_code=status.HTTP_302_FOUND
        )
        self.assertEqual(ClubMembership.objects.all().count(), 0)

        # Check login redirects back to join club
        create_test_user(email="user@example.com", password="123AbcTest")
        login_res = self.client.post(
            redirect_url, {"username": "user@example.com", "password": "123AbcTest"}
        )
        self.assertRedirects(login_res, url, target_status_code=status.HTTP_302_FOUND)

    def test_join_club_view_guest_register(self):
        """Should redirect to register page with query param."""

        join_url = join_club_url(self.club.id)
        url = f"{register_user_url()}?next={join_url}"

        # Check login redirects back to join club
        self.assertEqual(User.objects.count(), 0)
        register_res = self.client.post(
            url,
            {
                "name": "John Doe",
                "email": "user@example.com",
                "password": "123AbcTest",
                "confirm_password": "123AbcTest",
            },
        )
        self.assertRedirects(
            register_res, join_url, target_status_code=status.HTTP_302_FOUND
        )
        self.assertEqual(User.objects.count(), 1)

    def test_join_club_view_auth(self):
        """Should redirect to club home page, create membership."""

        # Create user
        user = create_test_user()
        self.client.force_login(user)

        # Generate urls
        url = join_club_url(self.club.id)
        redirect_url = club_home_url(self.club.id)

        # Send request, check if redirects
        res = self.client.get(url)
        self.assertRedirects(
            res, expected_url=redirect_url, status_code=status.HTTP_302_FOUND
        )
        self.assertEqual(ClubMembership.objects.all().count(), 1)

        # If user clicks link again, it should skip adding membership
        res = self.client.get(url)
        self.assertRedirects(
            res, expected_url=redirect_url, status_code=status.HTTP_302_FOUND
        )
        self.assertEqual(ClubMembership.objects.all().count(), 1)
