from clubs.defaults import INITIAL_CLUB_ROLES
from clubs.models import ClubRole
from clubs.services import ClubService
from clubs.tests.utils import create_test_club, create_test_team
from core.abstracts.tests import TestsBase
from events.tests.utils import create_test_event
from users.tests.utils import create_test_user


class ClubPermsBasicTests(TestsBase):
    """Club permissions tests."""

    def setUp(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)
        self.user = create_test_user()

        return super().setUp()

    def test_club_initial_roles(self):
        """When a club is created, it should contain initial roles."""

        self.assertEqual(ClubRole.objects.count(), len(INITIAL_CLUB_ROLES))

        member_role = ClubRole.objects.find_one(name="Member")
        self.assertIsNotNone(member_role)
        self.assertTrue(member_role.is_default)

        officer_role = ClubRole.objects.find_one(name="Officer")
        self.assertIsNotNone(officer_role)
        self.assertFalse(officer_role.is_default)

    def test_clubs_view_access(self):
        """All users should have view access to allow previews, but only members can see details."""

        self.assertTrue(self.user.has_perm("clubs.view_club", self.club))
        self.assertFalse(self.user.has_perm("clubs.view_club_details", self.club))

        self.service.add_member(self.user)
        self.assertTrue(self.user.has_perm("clubs.view_club", self.club))
        self.assertTrue(self.user.has_perm("clubs.view_club_details", self.club))
        self.assertFalse(self.user.has_perm("clubs.change_club"), self.club)

    def test_club_role_change_access(self):
        """Member should inherit change perms from club role."""

        role = self.club.roles.get(name="Officer")
        self.service.add_member(self.user, roles=[role])

        self.assertTrue(self.user.has_perm("clubs.change_club", self.club))

    def test_club_role_assignment_perms(self):
        """When a club member is reassigned a new role, their permissions should update."""

        self.service.add_member(self.user)
        self.assertFalse(self.user.has_perm("clubs.change_club", self.club))

        role = self.club.roles.get(name="Officer")
        self.service.set_member_role(self.user, role)
        self.assertTrue(self.user.has_perm("clubs.change_club", self.club))


class ClubScopedPermsTests(TestsBase):
    """
    Complex tests for club permissions.

    By default, there are two clubs, and the user is assigned to club 1.
    """

    def setUp(self):
        self.club1 = create_test_club()
        self.club2 = create_test_club()

        self.service1 = ClubService(self.club1)
        self.service2 = ClubService(self.club2)

        self.user = create_test_user()
        self.membership = self.service1.add_member(self.user)

    def test_club_roles_other_clubs(self):
        """Club roles should only apply to that club."""

        self.assertTrue(self.user.has_perm("clubs.view_club", self.club1))
        self.assertTrue(self.user.has_perm("clubs.view_club_details", self.club1))
        self.assertTrue(self.user.has_perm("clubs.view_club", self.club2))
        self.assertFalse(self.user.has_perm("clubs.view_club_details", self.club2))

    def test_club_event_perms(self):
        """Event permissions should be scoped to a club."""

        event1 = create_test_event(host=self.club1)
        self.assertTrue(self.user.has_perm("events.view_event", event1))
        self.assertTrue(self.user.has_perm("events.view_private_event", event1))
        self.assertFalse(self.user.has_perm("events.change_event", event1))

        # Check officer's permissions
        self.service1.set_member_role(self.user, "Officer")
        self.assertTrue(self.user.has_perm("events.change_event", event1))

        # Test access to other club's events
        event2 = create_test_event(host=self.club2)
        self.assertTrue(self.user.has_perm("events.view_event", event2))
        self.assertFalse(self.user.has_perm("events.view_private_event", event2))
        self.assertFalse(self.user.has_perm("events.change_event", event2))

    def test_club_team_perms(self):
        """Team permissions should be scoped to a club."""

        team1 = create_test_team(self.club1)
        team2 = create_test_team(self.club2)

        self.assertTrue(self.user.has_perm("clubs.view_team", team1))
        self.assertFalse(self.user.has_perm("clubs.change_team", team1))

        # Check officer's permission
        self.service1.set_member_role(self.user, "Officer")
        self.assertTrue(self.user.has_perm("clubs.change_team", team1))

        # Test access to other club's teams
        self.assertFalse(self.user.has_perm("clubs.view_team", team2))
        self.assertFalse(self.user.has_perm("clubs.change_team", team2))
