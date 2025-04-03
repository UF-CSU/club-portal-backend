from clubs.models import Team
from clubs.serializers import TeamCsvSerializer
from querycsv.tests.utils import UploadCsvTestsBase


class TeamCsvTests(UploadCsvTestsBase):
    """Unit tests for uploading csvs of teams."""

    model_class = Team
    serializer_class = TeamCsvSerializer

    # TODO: Add support for creating nested team roles
    # def test_upload_team_csv(self):
    #     """Should be able to upload a csv representing teams."""

    #     club = create_test_club()
    #     user = create_test_user()
    #     team = Team.objects.create(name="Test Team 1", club=club)
    #     TeamRole.objects.create(team=team, name="Test Role 1")
    #     TeamRole.objects.create(team=team, name="Test Role 2")

    #     payload = {
    #         "name": "Test Team 1",
    #         "club": club.name,
    #         "memberships[0].user": user.email,
    #         "memberships[0].roles": "Test Role 1, Test Role 2",
    #     }

    #     self.assertUploadPayload([payload])

    #     self.assertEqual(Team.objects.count(), 1)
    #     self.assertEqual(club.teams.count(), 1)

    #     team = Team.objects.first()
    #     self.assertEqual(team.memberships.count(), 1)

    #     member = team.memberships.first()
    #     self.assertEqual(member.user.email, user.email)
    #     self.assertEqual(TeamRole.objects.count(), 3)
    #     self.assertEqual(member.roles.count(), 2)
