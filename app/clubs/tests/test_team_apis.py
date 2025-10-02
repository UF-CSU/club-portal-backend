from django.urls import reverse

from clubs.models import Club, Team
from clubs.tests.utils import create_test_clubs, create_test_team
from core.abstracts.tests import PrivateApiTestsBase


def teams_list_url(club_id):
    return reverse("api-clubs:team-list", kwargs={"club_id": club_id})


class TeamPrivateApiTests(PrivateApiTestsBase):
    """Private routes for club teams."""

    def test_get_teams(self):
        """Should be able to get list of teams for a club."""

        CLUBS_COUNT = 5
        TEAMS_PER_CLUB_COUNT = 3

        create_test_clubs(count=CLUBS_COUNT)
        club1 = list(Club.objects.all())[0]
        club2 = list(Club.objects.all())[1]

        for _i in range(TEAMS_PER_CLUB_COUNT):
            create_test_team(club1)
            create_test_team(club2)

        url = teams_list_url(club1.id)
        res = self.client.get(url)
        self.assertResOk(res)

        res_body = res.json()
        self.assertEqual(len(res_body), TEAMS_PER_CLUB_COUNT)

        for res_team in res_body:
            self.assertTrue(
                Team.objects.filter(club=club1).filter(id=res_team["id"]).exists()
            )
