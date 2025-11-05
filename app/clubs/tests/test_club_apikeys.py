from core.abstracts.tests import PrivateApiTestsBase
from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase
from users.models import User
from users.serializers import UserCsvSerializer
from users.tests.utils import create_test_user

from clubs.models import ClubApiKey, Team, TeamMembership
from clubs.services import ClubService
from clubs.tests.utils import club_detail_url, club_roster_url, create_test_club


class ClubKeyApiTests(PrivateApiTestsBase):
    """Check what access api keys should have in the api."""

    def create_authenticated_user(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)
        self.key = ClubApiKey.objects.create(
            club=self.club,
            name="Test Key",
            permissions=[
                "clubs.view_club",
                "clubs.view_club_details",
                "clubs.view_clubmembership",
            ],
        )
        return self.key.user_agent

    def test_using_apikey(self):
        """A request should be able to be made using an API Key."""

        url = club_detail_url(self.club.id)
        res = self.client.get(url)
        self.assertResOk(res)

        # Check permission denied (not found) for other club
        club2 = create_test_club()

        url2 = club_detail_url(club2.id)
        res = self.client.get(url2)
        self.assertResNotFound(res)

    def test_accessing_roster(self):
        """User agent should access the club roster."""

        # Setup execs
        self.service.add_member(create_test_user(), roles=["President"])
        self.service.add_member(create_test_user(), roles=["Vice-President"])

        # Officers without a team
        self.service.add_member(create_test_user(), roles=["Officer"])

        # Director team (on roster)
        team = Team.objects.create(
            club=self.club, name="Directors", show_on_roster=True
        )
        TeamMembership.objects.create(team, create_test_user())

        # Secret Team (not on roster)
        team = Team.objects.create(
            club=self.club, name="Secret Team", show_on_roster=False
        )
        TeamMembership.objects.create(team, create_test_user())

        # Test api
        url = club_roster_url(self.club.id)
        res = self.client.get(url)
        self.assertResOk(res)

        # Check returned data
        data = res.json()
        self.assertIsNotNone(data.get("executives", None))
        self.assertIsNotNone(data.get("teams", None))

        self.assertLength(data["executives"], 2)
        self.assertLength(data["teams"], 1)
        self.assertEqual(data["teams"][0]["name"], "Directors")
        self.assertLength(data["teams"][0]["memberships"], 1)


class ApiKeyCsvUploadTests(UploadCsvTestsBase):
    """Edge cases around csv uploads."""

    model_class = User
    serializer_class = UserCsvSerializer

    def test_upload_user_csv_api_key(self):
        """
        Former Bug: Uploading users should not effect api key user.
        """

        club = create_test_club()
        key = ClubApiKey.objects.create(club=club, name=fake.title())
        self.assertIsNotNone(key.user_agent)
        self.assertIsNone(key.user_agent.email)

        # Upload csv of users
        payload = [
            {
                "profile.name": fake.name(),
                "email": fake.safe_email(),
                "club_memberships[0].club": club.name,
            }
        ]
        self.assertUploadPayload(payload)

        # Check useragent not modified
        key.refresh_from_db()
        self.assertIsNone(key.user_agent.email)
