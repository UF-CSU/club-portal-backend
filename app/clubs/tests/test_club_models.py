"""
Unit tests for generic model functions, validation, etc.
"""

from django.core import exceptions
from django.urls import reverse

from analytics.models import Link
from clubs.models import Club, ClubMembership, Event, Team, TeamMembership
from clubs.tests.utils import (
    CLUB_CREATE_PARAMS,
    CLUB_UPDATE_PARAMS,
    create_test_club,
    create_test_clubs,
)
from core.abstracts.tests import TestsBase
from lib.faker import fake
from users.tests.utils import create_test_user
from utils.helpers import get_full_url


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


class ClubEventTests(TestsBase):
    """Unit tests for club events."""

    def test_create_event_link(self):
        """Creating an event should createa new event attendance link."""

        self.assertEqual(Link.objects.count(), 0)

        club = create_test_club()
        event = Event.objects.create(club=club, name="Test Event")

        self.assertEqual(Link.objects.count(), 1)
        self.assertEqual(event.attendance_links.count(), 1)
        link = event.attendance_links.first()

        expected_url_path = reverse(
            "clubs:joinevent", kwargs={"club_id": event.club.id, "event_id": event.id}
        )
        expected_url = get_full_url(expected_url_path)
        self.assertEqual(link.target_url, expected_url)
        self.assertEqual(link.reference, "Default")

    def test_prevent_event_overlapping_clubs(self):
        """An event should not have fk to a club that exists in "other_clubs" field."""

        primary_club = create_test_club()
        clubs = create_test_clubs(count=5)

        event = Event.objects.create(club=primary_club, name=fake.title())
        event.other_clubs.add(*clubs)
        self.assertEqual(event.other_clubs.count(), 5)

        with self.assertRaises(exceptions.ValidationError):
            event.other_clubs.add(primary_club)
            event.save()


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
