from clubs.consts import INITIAL_TEAM_ROLES
from clubs.models import Team, TeamRole
from clubs.serializers import TeamCsvSerializer
from clubs.tests.utils import create_test_club, create_test_team
from querycsv.tests.utils import UploadCsvTestsBase
from users.tests.utils import create_test_user


class TeamCsvTests(UploadCsvTestsBase):
    """Unit tests for uploading csvs of teams."""

    model_class = Team
    serializer_class = TeamCsvSerializer

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
        self.assertEqual(TeamRole.objects.count(), 3 + len(INITIAL_TEAM_ROLES))
        self.assertEqual(member.roles.count(), 2)  # Should not add default role
