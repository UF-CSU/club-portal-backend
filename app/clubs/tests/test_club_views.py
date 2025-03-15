from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from clubs.models import ClubMembership, Event, EventAttendance
from clubs.services import ClubService
from clubs.tests.utils import club_home_url, create_test_club, join_club_url
from core.abstracts.tests import ViewTestsBase
from lib.faker import fake
from users.tests.utils import create_test_user, login_user_url, register_user_url

User = get_user_model()


def event_attendance_url(club_id: int, event_id: int):
    """Get url to log event attendance for member."""

    return reverse("clubs:joinevent", kwargs={"club_id": club_id, "event_id": event_id})


def event_attendance_done_url(club_id: int, event_id: int):
    """Get url to log event attendance for member."""

    return reverse(
        "clubs:joinevent_done", kwargs={"club_id": club_id, "event_id": event_id}
    )


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
                "first_name": "John",
                "last_name": "Doe",
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

    def test_join_event_view(self):
        """Should record attendance when joining event."""

        # Create user
        user = create_test_user()
        self.service.add_member(user)
        self.client.force_login(user)

        # Create event and url
        event = Event.objects.create(club=self.club, name=fake.title(3))
        url = event_attendance_url(club_id=self.club.id, event_id=event.id)
        redirect_url = event_attendance_done_url(
            club_id=self.club.id, event_id=event.id
        )

        self.assertEqual(EventAttendance.objects.count(), 0)

        # User visits attendance url, check if it redirects
        res = self.client.get(url)
        self.assertRedirects(
            res, expected_url=redirect_url, status_code=status.HTTP_302_FOUND
        )

        # Check attendance values
        self.assertEqual(EventAttendance.objects.count(), 1)

        ea = EventAttendance.objects.first()
        self.assertEqual(ea.event.id, event.id)
        self.assertEqual(ea.member.user.id, user.id)
