"""
Unit tests focused around REST APIs for the Clubs Service.
"""

from django.urls import reverse
from rest_framework.test import APIClient

from clubs.models import ClubApiKey, ClubFile, ClubRole
from clubs.services import ClubService
from clubs.tests.utils import (
    CLUBS_JOIN_URL,
    CLUBS_LIST_URL,
    club_apikey_list_url,
    club_detail_url,
    club_file_list_url,
    club_invite_url,
    club_list_url_member,
    club_members_list_url,
    create_test_club,
    create_test_clubs,
)
from core.abstracts.tests import EmailTestsBase, PrivateApiTestsBase, PublicApiTestsBase
from lib.faker import fake
from users.models import User
from users.tests.utils import create_test_user
from utils.testing import create_test_uploadable_image


class ClubsApiPublicTests(PublicApiTestsBase):
    """Tests for public routes on clubs api."""

    def test_invite_login_required(self):
        """An unauthenticated user should get an error when trying to send invites."""

        email_count = 5

        club = create_test_club()
        url = club_invite_url(club.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload)
        self.assertResUnauthorized(res)

    def test_using_apikey(self):
        """A request should be able to be made using an API Key."""

        club = create_test_club()

        key = ClubApiKey.objects.create(
            club=club,
            name="Test Key",
            permissions=[
                "clubs.view_club",
                "clubs.view_club_details",
                "clubs.view_clubmembership",
            ],
        )

        self.client = APIClient()
        self.client.force_authenticate(user=key.user_agent)

        url = club_detail_url(club.id)
        res = self.client.get(url)
        self.assertResOk(res)

        # Check permission denied (not found) for other club
        club2 = create_test_club()

        url2 = club_detail_url(club2.id)
        res = self.client.get(url2)
        self.assertResNotFound(res)

    def test_public_can_list_club_previews(self):
        """Public users should be able to list club previews without authentication."""

        url = reverse("api-clubs:clubpreview-list")
        res = self.client.get(url)

        self.assertResOk(res)

        data = res.json()["results"]
        self.assertIsInstance(data, list)

        expected_fields = ["name", "logo", "banner", "about", "founding_year"]
        for club in data:
            for field in expected_fields:
                self.assertIn(field, club, f"Club missing expected field: {field}")


class ClubsApiPrivateTests(PrivateApiTestsBase, EmailTestsBase):
    """Tests for club api routes."""

    def create_authenticated_user(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)

        user = create_test_user()
        self.service.add_member(user, roles=["President"], is_owner=True)

        return user

    def test_send_email_invites_api(self):
        """Should be able to send email invites via the API."""

        email_count = 5

        url = club_invite_url(self.club.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload)
        self.assertResAccepted(res)
        self.assertEmailsSent(email_count)

    def test_create_club_member_new_user(self):
        """Should be able to create club member without sending emails, will create user."""

        # Initial setup
        mem_email = fake.safe_email()
        payload = {
            "club_id": self.club.id,
            "user": {"email": mem_email, "send_account_email": False},
            "send_email": False,
            "is_owner": False,
            "redirect_to": fake.url(),
        }

        # Check initial state
        self.assertEqual(User.objects.filter(email=mem_email).count(), 0)

        # Api request
        url = club_members_list_url(self.club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(0)
        self.assertEqual(User.objects.filter(email=mem_email).count(), 1)

        user = User.objects.filter(email=mem_email).first()
        self.assertEqual(
            user.has_usable_password(),
            False,
            f"User {user} has a password",
        )
        self.assertEqual(user.club_memberships.count(), 1)

    def test_create_club_member_existing_user(self):
        """Should be able to create club member without sending email, use existing user."""

        # Initial setup
        target_user = create_test_user()
        payload = {
            "club_id": self.club.id,
            "user": {"email": target_user.email},
            "send_email": False,
            "is_owner": False,
            "redirect_to": fake.url(),
        }

        # Check initial state
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(target_user.club_memberships.count(), 0)

        # Api request
        url = club_members_list_url(self.club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(0)
        self.assertEqual(User.objects.count(), 2)

        target_user.refresh_from_db()
        self.assertEqual(target_user.club_memberships.count(), 1)

    def test_invite_club_admin(self):
        """Should be able to send an email invite to a new club admin."""

        # Initial setup
        mem_email = fake.safe_email()
        payload = {
            "club_id": self.club.id,
            "user": {"email": mem_email},
            "is_owner": True,
            "send_email": True,
            "redirect_to": fake.url(),
        }

        # Check initial state
        self.assertEqual(User.objects.filter(email=mem_email).count(), 0)

        # Api request
        url = club_members_list_url(self.club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        # Validate state
        self.assertEmailsSent(2)  # Emails: club invite, setup account
        self.assertEqual(User.objects.filter(email=mem_email).count(), 1)

        user = User.objects.filter(email=mem_email).first()
        self.assertEqual(
            user.has_usable_password(),
            False,
            f"User {user} as a password (hash): {user.password}",
        )
        self.assertEqual(user.club_memberships.count(), 1)

    def test_create_club_api_key(self):
        """Should be able to create an api key for a club."""

        url = club_apikey_list_url(self.club.id)

        payload = {
            "name": "Test Key",
            "description": "Lorem ipsum dolor sit amet.",
            "permissions": [
                "clubs.view_club",
                "clubs.view_clubmembership",
            ],
        }
        res = self.client.post(url, payload)
        self.assertResCreated(res)
        res_body = res.json()

        self.assertEqual(ClubApiKey.objects.count(), 1)
        key = ClubApiKey.objects.first()

        self.assertEqual(res_body["secret"], key.get_secret())

    def test_get_member_clubs(self):
        """User should only get clubs they are a member of."""

        CLUBS_COUNT = 5

        create_test_user()
        create_test_user()
        clubs = create_test_clubs(CLUBS_COUNT)

        ClubService(clubs[0]).add_member(self.user)
        ClubService(clubs[1]).add_member(self.user)
        ClubService(clubs[2]).add_member(self.user)

        url = club_list_url_member()
        res = self.client.get(url)

        res_body = res.json()

        # Check if there is only 3 clubs and 1 original club returned
        self.assertLength(res_body, 3 + 1)

    def test_join_clubs(self):
        """User should be able to join multiple clubs."""

        clubs = create_test_clubs(5)
        payload = {
            "clubs": [club.id for club in clubs[0:2]],
        }
        self.assertEqual(self.user.club_memberships.count(), 1)

        url = CLUBS_JOIN_URL
        self.client.post(url, payload, format="json")

        self.user.refresh_from_db()
        self.assertEqual(self.user.club_memberships.count(), len(payload["clubs"]) + 1)

        for id in payload["clubs"]:
            self.assertTrue(self.user.club_memberships.filter(club__id=id).exists())

    def test_upload_media(self):
        """User should be able to upload new media for a club."""

        club_file_count_before = ClubFile.objects.count()

        # Test uploading
        payload = {"file": create_test_uploadable_image()}
        url = club_file_list_url(self.club.id)
        res = self.client.post(url, payload, format="multipart")
        self.assertResCreated(res)

        data = res.json()
        self.assertStartsWith(data["file"], "http://")
        self.assertEqual(ClubFile.objects.count(), club_file_count_before + 1)

        club_file = ClubFile.objects.first()
        dir_path = "/".join(club_file.file.path.split("/")[0:-1])
        self.assertIn(str(self.club.id), dir_path)

        # Test viewing
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()

        self.assertIsInstance(data, list)
        self.assertLength(data, club_file_count_before + 1)

    # def test_filter_clubs_by_major(self):
    #     """Should return only cs clubs."""

    #     cs = Major.objects.create(name="Computer Science")
    #     art = Major.objects.create(name="Art")

    #     create_test_clubs(5, majors=[cs], members=[self.user])
    #     create_test_clubs(5, majors=[art], members=[self.user])

    #     url = CLUBS_LIST_URL + "?majors=Computer%20Science"
    #     res = self.client.get(url)
    #     data = res.json()

    #     self.assertLength(data, 5)
    #     for club in data:
    #         self.assertLength(club["majors"], 1)
    #         self.assertEqual(club["majors"][0], "Computer Science")


class ClubsApiPermsTests(PublicApiTestsBase):
    """Test fine-grained permissions handling in API."""

    CLUBS_COUNT = 5

    def setUp(self):
        super().setUp()

        self.user = create_test_user()
        self.clubs = create_test_clubs(self.CLUBS_COUNT)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_assigned_clubs(self):
        """User should only get assigned clubs."""

        url = CLUBS_LIST_URL

        # No clubs returned, not member of any
        res = self.client.get(url)
        self.assertResOk(res)
        data = res.json()

        self.assertLength(data, 0)

        svc = ClubService(self.clubs[0])
        svc.add_member(self.user)

        # Now has membership, 1 club returns
        res = self.client.get(url)
        self.assertResOk(res)
        data = res.json()

        self.assertLength(data, 1)

        resClub = data[0]
        self.assertEqual(resClub["id"], svc.obj.id)
        self.assertNotIn("members", resClub.keys())

    def test_get_assigned_club_detail(self):
        """User should only be able to get a club's details if assigned."""

        c1 = self.clubs[0]
        c2 = self.clubs[1]

        url1 = club_detail_url(c1.id)
        url2 = club_detail_url(club_id=c2.id)

        # Permission denied
        res = self.client.get(url1)
        self.assertResNotFound(res)

        # Permission denied
        res = self.client.get(url2)
        self.assertResNotFound(res)

        svc = ClubService(c1)
        svc.add_member(self.user)

        # Accepted, has proper role permissions
        res = self.client.get(url1)
        self.assertResOk(res)

        # Permission denied, not proper role for this club
        res = self.client.get(url2)
        self.assertResNotFound(res)

    def test_update_assigned_club(self):
        """A user should only be able to update a club if has proper permissions."""

        c1 = self.clubs[0]
        c2 = self.clubs[1]

        url1 = club_detail_url(c1.id)
        url2 = club_detail_url(c2.id)

        payload = {"name": "Updated name", "about": fake.paragraph()}

        # Initially denied, not member of club
        res = self.client.patch(url1, payload)
        self.assertResNotFound(res)

        svc = ClubService(c1)
        svc.add_member(self.user)

        # Denied, does not have permission
        res = self.client.patch(url1, payload)
        self.assertResForbidden(res)

        role = ClubRole.objects.create(
            c1,
            name="Editor",
            perm_labels=["clubs.change_club", "clubs.view_club"],
            # role_type=RoleType.CUSTOM,
        )
        svc.add_member_role(self.user, role)

        # Accepted
        res = self.client.patch(url1, payload)
        self.assertResOk(res)

        c1.refresh_from_db()
        self.assertEqual(c1.name, payload["name"])
        self.assertEqual(c1.about, payload["about"])

        # Rejected, not member of other club
        payload["name"] += "2"
        res = self.client.patch(url2, payload)
        self.assertResNotFound(res)

    def test_get_club_members(self):
        """User should only get members of clubs they are assigned to, and have perms to view."""

        club = self.clubs[0]
        svc = ClubService(club)
        role = ClubRole.objects.create(
            club, name="Subscriber", perm_labels=["clubs.view_club"]
        )
        svc.add_member(self.user, roles=[role])

        url = club_members_list_url(club.id)

        # Denied, does not have proper permissions
        res = self.client.get(url)
        self.assertResForbidden(res)

        role = ClubRole.objects.create(
            club, name="Member Viewer", perm_labels=["clubs.view_clubmembership"]
        )
        svc.add_member_role(self.user, role)

        # Accepted, has permission
        res = self.client.get(url)
        self.assertResOk(res)
