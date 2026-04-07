"""
Unit tests for generic model functions, validation, etc.
"""

from clubs.defaults import CLUB_ADMIN_ROLE_PERMISSIONS, CLUB_VIEWER_ROLE_PERMISSIONS
from clubs.models import (
    Club,
    ClubApiKey,
    ClubMembership,
    Team,
    TeamMembership,
    TeamRole,
)
from clubs.tests.utils import create_test_club, create_test_clubrole
from core.abstracts.models import RoleType
from core.abstracts.tests import TestsBase
from django.core import exceptions
from rest_framework.authtoken.models import Token
from users.models import User
from users.tests.utils import create_test_user
from utils.permissions import get_permission


class ClubModelTests(TestsBase):
    """Tests for club models."""

    def test_create_club(self):
        """Should create club, and set default logo."""

        club = Club.objects.create(name="Test Club")
        self.assertIsNotNone(club.logo)

    def test_one_membership_per_user(self):
        """A user should only be able to have one membership per club."""

        club = create_test_club()
        user = create_test_user()

        ClubMembership.objects.create(club=club, user=user)

        with self.assertRaises(exceptions.ValidationError):
            ClubMembership.objects.create(club=club, user=user)

    def test_create_api_key(self):
        """Test the process of creating an api key."""

        club = create_test_club()

        key = ClubApiKey.objects.create(club, name="Test Key")

        self.assertIsNotNone(key.user_agent)
        s1 = key.get_secret()

        self.assertEqual(Token.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

        s2 = key.get_secret()

        self.assertEqual(s1, s2)

        key.delete()

        self.assertEqual(ClubApiKey.objects.count(), 0)
        self.assertEqual(Token.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)

    def test_role_type_perms(self):
        """If role type is not custom, it should always have the listed perms."""

        club = create_test_club()
        role = create_test_clubrole(club)

        # Check default state
        self.assertEqual(role.role_type, RoleType.VIEWER)
        self.assertListEqual(role.perm_labels, CLUB_VIEWER_ROLE_PERMISSIONS, sort_lists=True)

        # Check state after adding permission
        role.permissions.add(get_permission("clubs.change_club"))
        role.save()
        role.refresh_from_db()
        self.assertEqual(role.role_type, RoleType.CUSTOM)

        # Check manually setting role type
        role.role_type = RoleType.VIEWER
        role.save()
        role.refresh_from_db()
        self.assertListEqual(role.perm_labels, CLUB_VIEWER_ROLE_PERMISSIONS, sort_lists=True)
        self.assertNotIn("clubs.change_club", role.perm_labels)

        # Check setting to admin
        role.role_type = RoleType.ADMIN
        role.save()
        self.assertListEqual(role.perm_labels, CLUB_ADMIN_ROLE_PERMISSIONS, sort_lists=True)

    def test_member_is_admin(self):
        """Should properly display if a user is an admin or not."""
        club = create_test_club()
        club2 = create_test_club()

        u0 = create_test_user()
        u1 = create_test_user()
        u2 = create_test_user()
        u3 = create_test_user()

        m_unassigned = ClubMembership.objects.create(club=club2, user=u3, is_owner=True)
        self.assertTrue(m_unassigned.is_admin)

        viewer_role = create_test_clubrole(club, role_type=RoleType.VIEWER)
        admin_role = create_test_clubrole(club, role_type=RoleType.ADMIN)

        # Check admin role for owner
        m0 = ClubMembership.objects.create(
            club=club, user=u2, roles=[viewer_role], is_owner=True
        )
        self.assertTrue(m0.is_admin)

        # Check viewer role
        m1 = ClubMembership.objects.create(club=club, user=u0, roles=[viewer_role])
        self.assertFalse(m1.is_admin)

        # Check admin role
        m2 = ClubMembership.objects.create(
            club=club, user=u1, roles=[viewer_role, admin_role]
        )
        self.assertTrue(m2.is_admin)

    def test_member_is_implicitly_role(self):
        """Should properly determine if a user is implicitly a role based on their custom permissions"""
        club = create_test_club()
        role = create_test_clubrole(club)
        self.assertEqual(role.role_type, RoleType.VIEWER)

        # Give user viewer role
        user = create_test_user()
        m = ClubMembership.objects.create(club=club, user=user, roles=[role])
        self.assertFalse(m.is_admin)

        # Add permissions to role (should now be custom)
        perms_mapping = role.get_permissions_by_role_type()
        admin_perms = perms_mapping[RoleType.ADMIN]
        for perm in admin_perms:
            role.permissions.add(get_permission(perm))
        role.save()
        role.refresh_from_db()
        self.assertEqual(role.role_type, RoleType.CUSTOM)

        # User should be admin
        self.assertTrue(m.is_admin)

    def test_member_matches_all_roles(self):
        """Member should match all roles they have permission for"""
        club = create_test_club()
        role = create_test_clubrole(club, role_type=RoleType.ADMIN)
        self.assertEqual(role.role_type, RoleType.ADMIN)

        user = create_test_user()
        m = ClubMembership.objects.create(club=club, user=user, roles=[role])
        self.assertTrue(m.is_admin)
        self.assertTrue(m.is_editor)
        self.assertTrue(m.is_viewer)
        self.assertTrue(m.is_follower)


class ClubTeamTests(TestsBase):
    """Unit tests for teams."""

    def test_assign_user_teams(self):
        """Should be able to add club members to a team."""

        club = create_test_club()
        user = create_test_user()

        ClubMembership.objects.create(club=club, user=user)

        team = Team.objects.create(name="Example Team", club=club)
        self.assertEqual(TeamRole.objects.count(), 1)
        role = team.roles.first()

        TeamMembership.objects.create(team=team, user=user)

        self.assertEqual(club.teams.count(), 1)
        self.assertEqual(user.team_memberships.count(), 1)

        membership: TeamMembership = user.team_memberships.first()
        self.assertEqual(membership.team.id, team.id)
        self.assertEqual(membership.roles.count(), 1)
        self.assertEqual(membership.roles.first().id, role.id)

    def test_team_user_must_club_member(self):
        """User can only be assigned to a team if they are a member of that club."""

        club = create_test_club()
        user = create_test_user()

        team = Team.objects.create(name="Example Team", club=club)

        # with self.assertRaises(exceptions.ValidationError):
        #     TeamMembership.objects.create(team=team, user=user).save()

        # Changed to add club membership instead
        TeamMembership.objects.create(team=team, user=user).save()
        self.assertEqual(user.club_memberships.count(), 1)
        self.assertEqual(team.memberships.count(), 1)

    def test_unique_team_per_club(self):
        """Should not allow duplicate team names per club."""

        club = create_test_club()

        Team.objects.create(name="Example Team", club=club)

        with self.assertRaises(exceptions.ValidationError):
            Team.objects.create(name="Example Team", club=club)

    def test_no_dup_users_per_club(self):
        """Should raise error if user is assigned multiple memberships to the same team."""

        club = create_test_club()
        user = create_test_user()
        team = Team.objects.create(name="Example Team", club=club)

        ClubMembership.objects.create(club=club, user=user)
        TeamMembership.objects.create(team=team, user=user)

        with self.assertRaises(exceptions.ValidationError):
            TeamMembership.objects.create(team=team, user=user)

    def test_one_default_team_role(self):
        """Should allow only one default team role."""

        club = create_test_club()
        team = Team.objects.create(name="Example team", club=club)

        # Sanity check initial role
        self.assertEqual(team.roles.count(), 1)
        r1 = team.roles.first()
        self.assertTrue(r1.is_default)

        # Create new role
        r2 = TeamRole.objects.create(team=team, name="Team Admin", is_default=False)
        self.assertEqual(team.roles.count(), 2)
        self.assertFalse(r2.is_default)

        # Check setting default
        r2.is_default = True
        r2.save()

        r2.refresh_from_db()
        r1.refresh_from_db()

        self.assertTrue(r2.is_default)
        self.assertFalse(r1.is_default)
