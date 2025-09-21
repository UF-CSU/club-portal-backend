from core.abstracts.tests import TestsBase

from users.models import User
from users.services import UserService
from users.tests.utils import create_test_user


class UserServiceTests(TestsBase):
    """Unit tests for users service."""

    def test_merge_users(self):
        """Should merge user models."""

        u1 = create_test_user()
        u2 = create_test_user()

        UserService.merge_users(users=User.objects.filter(id__in=[u1.id, u2.id]))

        self.assertTrue(User.objects.filter(id=u1.id).exists())
        self.assertFalse(User.objects.filter(id=u2.id).exists())
