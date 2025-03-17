from rest_framework import status

from events.models import EventAttendance
from clubs.tests.utils import create_test_club
from core.abstracts.tests import ViewTestsBase
from events.tests.utils import create_test_event
from users.forms import RegisterForm
from users.models import User
from users.tests.utils import register_user_url


class UserRegisterViewTests(ViewTestsBase):
    """Tests for user registration form."""

    user_payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "password": "abc123@Example",
        "confirm_password": "abc123@Example",
    }

    def setUp(self):
        self.club = create_test_club()
        self.event = create_test_event(host=self.club)

        return super().setUp()

    def assertUserFields(self, user: User, fields: dict):
        """Check name, email, and password fields for user."""
        self.assertEqual(user.profile.first_name, fields["first_name"])
        self.assertEqual(user.profile.last_name, fields["last_name"])
        self.assertEqual(user.profile.email, fields["email"])
        self.assertEqual(user.username, fields["email"])
        self.assertTrue(user.check_password(fields["password"]))

    def test_get_registration_page(self):
        """Should GET registration page."""
        url = register_user_url()
        res = self.assertRenders(url)
        self.assertHasForm(
            res, RegisterForm, initial_data={"club": None, "event": None}
        )

    def test_register_user(self):
        """Should create new user on post."""

        url = register_user_url()
        payload = self.user_payload

        self.assertEqual(User.objects.all().count(), 0)

        res = self.client.post(url, payload, follow=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(User.objects.all().count(), 1)
        user: User = User.objects.all().first()

        self.assertUserFields(user, payload)

    def test_register_user_with_club(self):
        """Should create new user, add to club."""

        url = register_user_url()
        payload = {**self.user_payload, "club": self.club.id}

        self.assertEqual(User.objects.all().count(), 0)

        res = self.client.post(url, payload, follow=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(User.objects.all().count(), 1)
        user: User = User.objects.all().first()

        self.assertUserFields(user, payload)
        self.assertIn(
            self.club.id, list(user.club_memberships.values_list("club__id", flat=True))
        )

    def test_register_user_with_event(self):
        """Should create new user, add to club, mark as attended."""
        url = register_user_url()
        payload = {**self.user_payload, "event": self.event.id}

        self.assertEqual(User.objects.all().count(), 0)

        res = self.client.post(url, payload, follow=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(User.objects.all().count(), 1)
        user: User = User.objects.all().first()

        self.assertUserFields(user, payload)
        self.assertIn(
            self.club.id, list(user.club_memberships.values_list("club__id", flat=True))
        )
        self.assertEqual(
            EventAttendance.objects.filter(event=self.event, user=user).count(), 1
        )
