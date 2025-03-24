from unittest.mock import Mock, patch
from clubs.models import Club, ClubMembership, ClubRole
from clubs.tests.utils import create_test_club
from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase
from users.models import Profile, SocialProfile, User
from users.serializers import UserCsvSerializer
from users.tests.utils import create_test_user


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
                "socials[0].social_type": "linkedin",
                "socials[0].username": "@example",
                "socials[1].social_type": "discord",
                "socials[1].username": "@somediscord",
            },
        ]

        self.assertUploadPayload(payload)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Club.objects.count(), 2)
        self.assertEqual(ClubMembership.objects.count(), 3)
        self.assertEqual(ClubRole.objects.count(), roles_before)
        self.assertEqual(SocialProfile.objects.count(), 2)

    def test_upload_update_user_csv(self):
        """Should be able to upload csv and update users."""

        # clubs = create_test_clubs(count=2).order_by("-id")
        c1 = create_test_club(name="Test Club 1")
        c2 = create_test_club(name="Test Club 2")

        ClubRole.objects.create(club=c1, name="Test Role 1", default=True)
        ClubRole.objects.create(club=c1, name="Test Role 2")
        ClubRole.objects.create(club=c2, name="Test Role 3", default=True)
        ClubRole.objects.create(club=c2, name="Test Role 4")

        roles_before = ClubRole.objects.count()

        u1 = create_test_user(email=fake.safe_email())
        u2 = create_test_user(email=fake.safe_email())

        payload = [
            {
                "email": u1.email,
                "club_memberships[0].club": c1.name,
            },
            {
                "email": u2.email,
                "username": fake.user_name(),
                "profile.first_name": fake.first_name(),
                "profile.last_name": fake.last_name(),
                "club_memberships[0].club": c1.name,
                "club_memberships[0].roles": "Test Role 1",
                "club_memberships[1].club": c2.name,
                "club_memberships[1].roles": "Test Role 3, Test Role 4",
                "socials[0].social_type": "linkedin",
                "socials[0].username": "@example",
                "socials[1].social_type": "discord",
                "socials[1].username": "@somediscord",
            },
        ]

        self.assertUploadPayload(payload)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Club.objects.count(), 2)
        self.assertEqual(ClubMembership.objects.count(), 3)
        self.assertEqual(ClubRole.objects.count(), roles_before)
        self.assertEqual(SocialProfile.objects.count(), 2)

    @patch("requests.get")
    def test_upload_user_profile_image(self, mock_get):
        """When uploading user csv, should upload profile images."""

        mock_get.return_value = Mock()
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = fake.image((300, 300), "png")

        payload = {
            "email": fake.safe_email(),
            "profile.image": "https://example.com/image.png",
        }

        self.assertUploadPayload([payload])

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Profile.objects.count(), 1)

        user = User.objects.first()
        self.assertTrue(user.profile.image)
        self.assertEqual(user.profile.image.width, 300)
        self.assertEqual(user.profile.image.height, 300)
