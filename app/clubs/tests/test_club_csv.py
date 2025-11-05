from django.utils import timezone
from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase
from users.models import User

from clubs.models import Club, ClubFile, ClubMembership, ClubRole, ClubSocialProfile
from clubs.serializers import ClubCsvSerializer, ClubMembershipCsvSerializer
from clubs.tests.utils import create_test_club


class ClubCsvUploadTests(UploadCsvTestsBase):
    """Test upload csv functionality for clubs."""

    model_class = Club
    serializer_class = ClubCsvSerializer

    def test_club_csv_fields(self):
        """Getting a list of available fields should return correct fields."""

        expected_fields = [
            "socials[n].social_type",
            "socials[n].username",
            "socials[n].url",
            "socials[n].order",
        ]
        actual_fields = list(self.service.flat_fields.keys())

        for field in expected_fields:
            self.assertIn(field, actual_fields)

    def test_club_csv_serializer(self):
        """Club csv serializer should work properly."""

        payload = {
            "name": fake.title(),
            "alias": "ABC",
            "contact_email": fake.safe_email(),
            "about": fake.paragraph(),
        }
        self.repo.create(**payload)
        payload = {
            **payload,
            "tags": "one, two, three",
            "socials[0].social_type": "discord",
            "socials[0].username": "@example_user",
        }

        serializer = self.serializer_class(data=payload, flat=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNotNone(serializer.instance)

    def test_create_club_from_csv(self):
        """Uploading a csv for a club should create club."""

        payload = {
            "name": fake.title(),
            "alias": "ABC",
            "logo": fake.image_url(placeholder_url="https://dummyimage.com/200x200"),
        }

        file = self.data_to_csv([payload])
        success, failed = self.service.upload_csv(file=file)
        self.assertLength(success, 1, failed)
        self.assertLength(failed, 0)

        self.assertEqual(self.repo.count(), 1)
        obj: Club = self.repo.first()
        self.assertEqual(obj.name, payload["name"])
        self.assertEqual(obj.alias, payload["alias"])
        self.assertIsNotNone(obj.logo)
        self.assertNotEqual(ClubFile.objects.count(), 0)

        # Verify that the image is the one that was downloaded
        self.assertStartsWith(obj.logo.display_name, "200x200")

    # def test_updating_club_from_csv(self):
    #     """Uploading a csv should update existing clubs."""

    #     club = create_test_club()

    #     payload = {
    #         "id": club.pk,
    #         "name": "Updated name",
    #         "logo": fake.image_url(placeholder_url="https://dummyimage.com/200x200"),
    #     }

    #     self.assertUploadPayload([payload])

    #     self.assertEqual(Club.objects.count(), 1)
    #     club.refresh_from_db()
    #     self.assertEqual(club.name, payload["name"])
    #     self.assertStartsWith(club.logo.display_name, "200x200")
    #     club_file_count_before = ClubFile.objects.count()

    #     # Check reuploading csv
    #     self.assertUploadPayload([payload])
    #     self.assertEqual(Club.objects.count(), 1)
    #     club.refresh_from_db()
    #     self.assertEqual(club.name, payload["name"])
    #     self.assertStartsWith(club.logo.display_name, "200x200")

    #     # Ensure no new files were created
    #     self.assertEqual(ClubFile.objects.count(), club_file_count_before)

    def test_create_club_socials(self):
        """Uploading a club with socials should create club and social profiles."""

        payload = {
            "name": fake.title(),
            "alias": "ABC",
            "socials[0].social_type": "discord",
            "socials[0].username": "@example_user",
            "socials[1].social_type": "instagram",
            "socials[1].username": "@instauser",
            "socials[1].url": fake.url(),
        }

        file = self.data_to_csv([payload])
        success, failed = self.service.upload_csv(file=file)
        self.assertLength(success, 1, failed)
        self.assertLength(failed, 0)

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["name"])

        self.assertEqual(ClubSocialProfile.objects.count(), 2)
        self.assertEqual(obj.socials.count(), 2)

        s1 = ClubSocialProfile.objects.filter(username=payload["socials[0].username"])
        self.assertTrue(s1.exists())
        self.assertEqual(s1.first().social_type, payload["socials[0].social_type"])

        s2 = ClubSocialProfile.objects.filter(username=payload["socials[1].username"])
        self.assertTrue(s2.exists())
        self.assertEqual(s2.first().social_type, payload["socials[1].social_type"])
        self.assertEqual(s2.first().url, payload["socials[1].url"])

    def test_update_club_socials(self):
        """Uploading a club with socials should create club and social profiles."""

        default_payload = {
            "name": fake.title(),
            "alias": "ABC",
        }

        self.repo.create(**default_payload)

        payload = {
            **default_payload,
            "socials[0].social_type": "discord",
            "socials[0].username": "@example_user",
            "socials[1].social_type": "instagram",
            "socials[1].username": "@instauser",
            "socials[1].url": fake.url(),
        }

        file = self.data_to_csv([payload])
        success, failed = self.service.upload_csv(file=file)
        self.assertLength(success, 1, failed)
        self.assertLength(failed, 0)

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload["name"])

        self.assertEqual(ClubSocialProfile.objects.count(), 2)
        self.assertEqual(obj.socials.count(), 2)

        s1 = ClubSocialProfile.objects.filter(username=payload["socials[0].username"])
        self.assertTrue(s1.exists())
        self.assertEqual(s1.first().social_type, payload["socials[0].social_type"])

        s2 = ClubSocialProfile.objects.filter(username=payload["socials[1].username"])
        self.assertTrue(s2.exists())
        self.assertEqual(s2.first().social_type, payload["socials[1].social_type"])
        self.assertEqual(s2.first().url, payload["socials[1].url"])

    def test_upload_club_json(self):
        """Should upload clubs from json."""

        payload = [
            {
                "OrganizationName": "Computing Student Union",
                "Acronym": "CSU",
                "OrganizationDescription": fake.paragraph(),
                "DateCreated": (
                    timezone.now() - timezone.timedelta(days=365 * 2)
                ).isoformat(),
                "LastUpdated": (
                    timezone.now() - timezone.timedelta(days=365 * 1)
                ).isoformat(),
                "OrganizationState": True,
                "OrganizationTypeName": "Example Type",
                "SupportingInstitution": fake.title(),
                "ElectionMonth": "November",
                "CurrentlyRegistering": True,
            }
        ]

        mappings = [
            {"column_name": "OrganizationName", "field_name": "name"},
            {"column_name": "Acronym", "field_name": "alias"},
            {"column_name": "OrganizationDescription", "field_name": "about"},
            {"column_name": "DateCreated", "field_name": "SKIP"},
            {"column_name": "LastUpdated", "field_name": "SKIP"},
            {"column_name": "OrganizationState", "field_name": "SKIP"},
            {"column_name": "OrganizationTypeName", "field_name": "SKIP"},
            {"column_name": "SupportingInstitution", "field_name": "SKIP"},
            {"column_name": "ElectionMonth", "field_name": "SKIP"},
            {"column_name": "CurrentlyRegistering", "field_name": "SKIP"},
        ]

        file = self.dump_json(payload)
        success, failed = self.service.upload_csv(file=file, custom_field_maps=mappings)
        self.assertEqual(len(success), 1, failed)
        self.assertEqual(len(failed), 0)
        self.assertEqual(self.repo.count(), 1)

        self.assertEqual(self.repo.count(), 1)
        obj = self.repo.first()
        self.assertEqual(obj.name, payload[0]["OrganizationName"])
        self.assertEqual(obj.alias, payload[0]["Acronym"])
        self.assertEqual(obj.about, payload[0]["OrganizationDescription"])


class ClubMembershipCsvUploadTests(UploadCsvTestsBase):
    """Test upload csv functionality for club memberships."""

    model_class = ClubMembership
    serializer_class = ClubMembershipCsvSerializer

    def setUp(self):
        self.club = create_test_club()
        self.club2 = create_test_club()
        return super().setUp()

    def get_create_params(self, **kwargs):
        return {"club": self.club, "user": self.user, **kwargs}

    def test_create_club_memberships(self):
        """Should create club memberships from a csv."""

        # Initialize data
        payload = [
            {
                "club": self.club.id,
                "user.email": fake.safe_email(),
                "roles": ["Member", "New Role"],
            }
            for _ in range(self.dataset_size)
        ]
        file = self.data_to_csv(payload)

        # Call service
        _, failed = self.service.upload_csv(file=file)

        # Validate database,
        # Memberships are non-standard schemas so we do manual testing
        memberships = self.repo.all()
        self.assertEqual(memberships.count(), self.dataset_size, failed)

        for expected in payload:
            self.assertTrue(User.objects.filter(email=expected["user.email"]).exists())

            for role in expected["roles"]:
                self.assertTrue(
                    ClubRole.objects.filter(name=role, club=self.club).exists()
                )

            self.assertTrue(
                self.repo.filter(
                    club=expected["club"], user__email=expected["user.email"]
                ).exists()
            )
