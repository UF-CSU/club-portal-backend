from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase
from users.tests.utils import create_test_user
from utils.helpers import str_to_list

from clubs.defaults import INITIAL_TEAM_ROLES
from clubs.models import Team, TeamRole
from clubs.serializers import TeamCsvSerializer
from clubs.tests.utils import create_test_club, create_test_team


class TeamCsvTests(UploadCsvTestsBase):
    """Unit tests for uploading csvs of teams."""

    model_class = Team
    serializer_class = TeamCsvSerializer

    default_roles_count = len(INITIAL_TEAM_ROLES)

    def test_upload_team_csv(self):
        """Should be able to upload a csv representing teams."""

        club = create_test_club()
        user = create_test_user()

        # Test with duplicate roles
        t2 = create_test_team(club=club, name="Test Team 2", clear_roles=True)
        TeamRole.objects.create(team=t2, name="Test Role 1")

        # Upload CSV
        payload = {
            "name": "Test Team 1",
            "club": club.name,
            "members[0].user": user.email,
            "members[0].roles": "Test Role 1, Test Role 2",
        }

        self.assertUploadPayload([payload])

        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(club.teams.count(), 2)
        t1 = Team.objects.get(name="Test Team 1")

        self.assertEqual(t1.memberships.count(), 1)

        member = t1.memberships.first()
        self.assertEqual(member.user.email, user.email)
        self.assertEqual(TeamRole.objects.count(), 3 + self.default_roles_count)
        self.assertEqual(member.roles.count(), 2)  # Should not add default role

    # TODO: Check if memberships can be updated
    def test_update_teams_csv(self):
        """Uploading a csv for a team should update the team and memberships."""

        club = create_test_club()
        u1 = create_test_user()  # Check setting roles
        u2 = create_test_user()  # Check skipping empty roles

        # Create team, and membership
        payload = {
            "name": fake.title(),
            "club": club.name,
            "members[0].user": u1.email,
            "members[1].user": u2.email,
            "members[1].roles": "Test Role",
        }

        self.assertUploadPayload([payload])
        self.assertEqual(Team.objects.count(), 1)
        team = Team.objects.first()

        # Update the team
        payload = {
            "id": team.id,
            "name": team.name + " updated",
            "club": club.name,
            "members[0].user": u1.email,
            "members[0].roles": "Role 1, Role 2",
            "members[1].user": u2.email,
            "members[1].roles": "",
        }

        self.assertUploadPayload([payload])

        # Team should have updated
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(TeamRole.objects.count(), 3 + self.default_roles_count)

        team.refresh_from_db()
        self.assertEqual(team.name, payload["name"])
        self.assertEqual(team.memberships.count(), 2)

        # Membership roles should have been set, not appended
        member = team.memberships.get(user__email=u1.email)
        self.assertEqual(member.roles.count(), 2)
        roles = list(member.roles.all().values_list("name", flat=True))
        self.assertListEqual(
            roles, str_to_list(payload["members[0].roles"]), sort_lists=True
        )

        # Membership roles should not be updated if empty field
        member = team.memberships.get(user__email=u2.email)
        self.assertEqual(member.roles.count(), 1)
        self.assertEqual(member.roles.first().name, "Test Role")
