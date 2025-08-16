from django.core import exceptions

from core.abstracts.tests import TestsBase
from users.models import VerifiedEmail
from users.tests.utils import create_test_user


class UserEmailEdgeCaseTests(TestsBase):
    """Unit tests for different edge cases that could occur with user emails."""

    def test_user_having_someone_elses_verified_email(self):
        """Should prevent user from having someone elses verified email."""

        TARGET_EMAIL = "user@ufl.edu"

        u1 = create_test_user(email=TARGET_EMAIL)
        u2 = create_test_user()
        VerifiedEmail.objects.create(user=u1, email=TARGET_EMAIL)

        u1.email = "new@example.com"
        u1.save()

        with self.assertRaises(exceptions.ValidationError):
            u2.email = TARGET_EMAIL
            u2.save()

        with self.assertRaises(exceptions.ValidationError):
            u2.username = TARGET_EMAIL
            u2.save()

        with self.assertRaises(exceptions.ValidationError):
            u2.profile.school_email = TARGET_EMAIL
            u2.profile.save()

    def test_username_email_uniqueness(self):
        """Should raise an error if user attempts to save username as email that's not theirs."""

        user = create_test_user(username="loremipsum", email="user@example.com")

        with self.assertRaises(exceptions.ValidationError):
            user.username = "lorem@example.com"
            user.save()

        # Ensure they can use their own email
        user.username = "user@example.com"
        user.save()

    def test_duplicate_email_school_email_values(self):
        """Should prevent school email and user email from overlapping."""

        u1 = create_test_user(email="user@example.com")
        u2 = create_test_user(email="user@ufl.edu")

        self.assertEqual(u2.profile.school_email, "user@ufl.edu")

        # User 2 changes default email
        u2.email = "user2@example.com"
        u2.save()

        # User 1 tries to set main email as user2's ufl email
        with self.assertRaises(exceptions.ValidationError):
            u1.email = "user@ufl.edu"
            u1.save()
