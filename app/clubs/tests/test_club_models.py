"""
Unit tests for generic model functions, validation, etc.
"""

from django.core import exceptions
from rest_framework.authtoken.models import Token

from clubs.models import ClubApiKey, ClubMembership, Team, TeamMembership, TeamRole
from clubs.tests.utils import create_test_club
from core.abstracts.tests import TestsBase
from users.models import User
from users.tests.utils import create_test_user

# class BaseModelTests(TestsBase):
#     """Base tests for django models."""

#     model = Club
#     create_params = CLUB_CREATE_PARAMS
#     update_params = CLUB_UPDATE_PARAMS

#     def test_create_model(self):
#         """Should create model."""
#         obj = self.model.objects.create(**self.create_params)
#         self.assertIsNotNone(obj.created_at)

#         for key, expected_value in self.create_params.items():
#             actual_value = getattr(obj, key)

#             self.assertEqual(actual_value, expected_value)

#     def test_update_model(self):
#         """Should update model."""

#         obj = self.model.objects.create(**self.create_params)

#         for key, expected_value in self.update_params.items():
#             actual_value = getattr(obj, key)
#             self.assertNotEqual(actual_value, expected_value)

#             setattr(obj, key, expected_value)
#             obj.save()

#             actual_value = getattr(obj, key)
#             self.assertEqual(actual_value, expected_value)

#     def test_delete_model(self):
#         """Should delete model."""

#         obj = self.model.objects.create(**self.create_params)

#         obj_count = self.model.objects.all().count()
#         self.assertEqual(obj_count, 1)

#         self.model.objects.filter(id=obj.id).delete()

#         obj_count = self.model.objects.all().count()
#         self.assertEqual(obj_count, 0)


class ClubModelTests(TestsBase):
    """Tests for club models."""

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
        self.assertTrue(r1.default)

        # Create new role
        r2 = TeamRole.objects.create(team=team, name="Team Admin", default=False)
        self.assertEqual(team.roles.count(), 2)
        self.assertFalse(r2.default)

        # Check setting default
        r2.default = True
        r2.save()

        r2.refresh_from_db()
        r1.refresh_from_db()

        self.assertTrue(r2.default)
        self.assertFalse(r1.default)
