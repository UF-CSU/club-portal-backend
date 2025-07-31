from clubs.models import ClubApiKey
from clubs.tests.utils import create_test_club
from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase
from users.models import User
from users.serializers import UserCsvSerializer


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
