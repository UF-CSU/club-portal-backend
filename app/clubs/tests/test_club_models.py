"""
Unit tests for generic model functions, validation, etc.
"""

from django.core import exceptions

from clubs.models import Club, ClubMembership, Team, TeamMembership
from clubs.tests.utils import CLUB_CREATE_PARAMS, CLUB_UPDATE_PARAMS, create_test_club
from core.abstracts.tests import TestsBase
from users.tests.utils import create_test_user


class BaseModelTests(TestsBase):
    """Base tests for django models."""

    model = Club
    create_params = CLUB_CREATE_PARAMS
    update_params = CLUB_UPDATE_PARAMS

    def test_create_model(self):
        """Should create model."""
        obj = self.model.objects.create(**self.create_params)
        self.assertIsNotNone(obj.created_at)

        for key, expected_value in self.create_params.items():
            actual_value = getattr(obj, key)

            self.assertEqual(actual_value, expected_value)

    def test_update_model(self):
        """Should update model."""

        obj = self.model.objects.create(**self.create_params)

        for key, expected_value in self.update_params.items():
            actual_value = getattr(obj, key)
            self.assertNotEqual(actual_value, expected_value)

            setattr(obj, key, expected_value)
            obj.save()

            actual_value = getattr(obj, key)
            self.assertEqual(actual_value, expected_value)

    def test_delete_model(self):
        """Should delete model."""

        obj = self.model.objects.create(**self.create_params)

        obj_count = self.model.objects.all().count()
        self.assertEqual(obj_count, 1)

        self.model.objects.filter(id=obj.id).delete()

        obj_count = self.model.objects.all().count()
        self.assertEqual(obj_count, 0)


class ClubModelTests(TestsBase):
    """Tests for club models."""

    def test_one_membership_per_user(self):
        """A user should only be able to have one membership per club."""

        club = create_test_club()
        user = create_test_user()

        ClubMembership.objects.create(club=club, user=user)

        with self.assertRaises(exceptions.ValidationError):
            ClubMembership.objects.create(club=club, user=user)


class ClubTeamTests(TestsBase):
    """Unit tests for teams."""

    def test_assign_user_teams(self):
        """Should be able to add club members to a team."""

        club = create_test_club()
        user = create_test_user()

        ClubMembership.objects.create(club=club, user=user)

        team = Team.objects.create(name="Example Team", club=club)
        TeamMembership.objects.create(team=team, user=user)

        self.assertEqual(club.teams.count(), 1)
        self.assertEqual(user.team_memberships.count(), 1)
        self.assertEqual(user.team_memberships.first().team.id, team.id)

    def test_team_user_must_club_member(self):
        """User can only be assigned to a team if they are a member of that club."""

        club = create_test_club()
        user = create_test_user()

        team = Team.objects.create(name="Example Team", club=club)

        with self.assertRaises(exceptions.ValidationError):
            TeamMembership.objects.create(team=team, user=user).save()

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
