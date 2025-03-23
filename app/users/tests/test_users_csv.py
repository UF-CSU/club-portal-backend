from clubs.models import Club, ClubMembership, ClubRole
from clubs.tests.utils import create_test_club
from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase
from users.models import User
from users.serializers import UserCsvSerializer


class UserCsvTests(UploadCsvTestsBase):
    """Test the ability to manage users via csvs."""

    model_class = User
    serializer_class = UserCsvSerializer

    def test_upload_create_user_csv(self):
        """Should be able to upload csv and create users."""

        # clubs = create_test_clubs(count=2).order_by("-id")
        c1 = create_test_club(name="Test Club 1")
        c2 = create_test_club(name="Test Club 2")

        ClubRole.objects.create(club=c1, name="Test Role 1", default=True)
        ClubRole.objects.create(club=c1, name="Test Role 2")
        ClubRole.objects.create(club=c2, name="Test Role 3", default=True)
        ClubRole.objects.create(club=c2, name="Test Role 4")

        roles_before = ClubRole.objects.count()

        payload = [
            {
                "email": fake.safe_email(),
                "club_memberships[0].club": c1.name,
            },
            {
                "email": fake.safe_email(),
                "username": fake.user_name(),
                "profile.first_name": fake.first_name(),
                "profile.last_name": fake.last_name(),
                "club_memberships[0].club": c1.name,
                "club_memberships[0].roles": "Test Role 1",
                "club_memberships[1].club": c2.name,
                "club_memberships[1].roles": "Test Role 3, Test Role 4",
            },
        ]

        self.assertUploadPayload(payload)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Club.objects.count(), 2)
        self.assertEqual(ClubMembership.objects.count(), 3)

        self.assertEqual(ClubRole.objects.count(), roles_before)
