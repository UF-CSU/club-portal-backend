from clubs.tests.utils import create_test_club
from core.abstracts.tests import TestsBase
from events.tests.utils import create_test_event
from polls.tests.utils import create_test_poll, create_test_pollsubmission
from users.models import User
from users.services import UserService
from users.tests.utils import create_test_user


class UserServiceTests(TestsBase):
    """Unit tests for users service."""

    def test_merge_users_info(self):
        """Should merge user profile info."""

        u1 = create_test_user(email="jdoe@example.com", profile={"name": "John Doe"})
        u2 = create_test_user(email="john@ufl.edu", profile={"name": "Johnny Doe"})

        user = UserService.merge_users(users=[u1, u2])

        self.assertTrue(User.objects.filter(id=u1.id).exists())
        self.assertFalse(User.objects.filter(id=u2.id).exists())
        self.assertEqual(user.id, u1.id)

        self.assertEqual(user.email, "jdoe@example.com")
        self.assertEqual(user.profile.name, "John Doe")
        self.assertEqual(user.profile.school_email, "john@ufl.edu")

    def test_merge_users_relations(self):
        """Should merge user models and their relationships."""

        # Associate data with each user
        u1 = create_test_user()
        u2 = create_test_user()

        # Each user is a member of a different club, and member of same club
        c1 = create_test_club(members=[u1])
        c2 = create_test_club(members=[u2])
        c3 = create_test_club(members=[u1, u2])

        # Each club has an event
        e1 = create_test_event(host=c1)
        e2 = create_test_event(host=c2)
        e3 = create_test_event(host=c3)

        # Each event has a poll
        p1 = create_test_poll(event=e1)
        p2 = create_test_poll(event=e2)
        p3 = create_test_poll(event=e3)

        # Each user creates submission for each poll (irl, there will prob only be one submission for each
        # poll since a person wouldn't want to submit a poll more than once)
        s1 = create_test_pollsubmission(poll=p1, user=u1)
        s2 = create_test_pollsubmission(poll=p1, user=u2)
        s3 = create_test_pollsubmission(poll=p2, user=u1)
        s4 = create_test_pollsubmission(poll=p2, user=u2)
        s5 = create_test_pollsubmission(poll=p3, user=u1)
        s6 = create_test_pollsubmission(poll=p3, user=u2)

        user = UserService.merge_users(users=User.objects.filter(id__in=[u1.id, u2.id]))

        self.assertTrue(User.objects.filter(id=u1.id).exists())
        self.assertFalse(User.objects.filter(id=u2.id).exists())
        self.assertEqual(user.id, u1.id)

        # Check that the merged user is a part of all 3 clubs
        self.assertEqual(user.club_memberships.count(), 3)
        self.assertEqual(user.clubs.count(), 3)
        self.assertEqual(user.clubs.filter(id__in=[c1.id, c2.id, c3.id]).count(), 3)

        # Check that the user is attached to each poll submission
        s1.refresh_from_db()
        s2.refresh_from_db()
        s3.refresh_from_db()
        s4.refresh_from_db()
        s5.refresh_from_db()
        s6.refresh_from_db()

        self.assertEqual(s1.user.id, user.id)
        self.assertEqual(s2.user.id, user.id)
        self.assertEqual(s3.user.id, user.id)
        self.assertEqual(s4.user.id, user.id)
        self.assertEqual(s5.user.id, user.id)
        self.assertEqual(s6.user.id, user.id)
