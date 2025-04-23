from clubs.models import Team, TeamRole
from clubs.serializers import TeamCsvSerializer
from clubs.tests.utils import create_test_club
from querycsv.tests.utils import UploadCsvTestsBase
from users.tests.utils import create_test_user


class TeamCsvTests(UploadCsvTestsBase):
    """Unit tests for uploading csvs of teams."""

    model_class = Team
    serializer_class = TeamCsvSerializer

    # TODO: Add support for creating nested team roles
    def test_upload_team_csv(self):
        """Should be able to upload a csv representing teams."""

        club = create_test_club()
        user = create_test_user()
        team = Team.objects.create(name="Test Team 1", club=club)
        TeamRole.objects.filter(team=team).delete()

        TeamRole.objects.create(team=team, name="Test Role 1")
        TeamRole.objects.create(team=team, name="Test Role 2")

        # Test with duplicate roles
        t2 = Team.objects.create(name="Test Team 2", club=club)
        TeamRole.objects.filter(team=t2).delete()
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

        team = Team.objects.get(name="Test Team 1")
        self.assertEqual(team.memberships.count(), 1)

        member = team.memberships.first()
        self.assertEqual(member.user.email, user.email)
        self.assertEqual(TeamRole.objects.count(), 3)
        self.assertEqual(member.roles.count(), 2)
