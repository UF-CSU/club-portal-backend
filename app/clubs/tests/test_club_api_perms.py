"""
Unit tests focused around REST APIs for the Clubs Service.
"""

from core.abstracts.tests import PublicApiTestsBase
from lib.faker import fake
from rest_framework.test import APIClient
from users.tests.utils import create_test_user

from clubs.models import ClubRole
from clubs.services import ClubService
from clubs.tests.utils import (
    CLUBS_LIST_URL,
    club_detail_url,
    club_list_url_member,
    club_members_detail_url,
    club_members_list_url,
    create_test_club,
    create_test_clubs,
)


class ManyClubsApiPermsTests(PublicApiTestsBase):
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

    def test_is_admin_none(self):
        """Tests club response if is_admin is None"""

        MY_CLUB_COUNT = 3

        # clubs = create_test_clubs(CLUBS_COUNT)

        ClubService(self.clubs[0]).add_member(self.user, roles=["President"])
        ClubService(self.clubs[1]).add_member(self.user, roles=["Member"])
        ClubService(self.clubs[2]).add_member(self.user, roles=["Member"])

        url = club_list_url_member()

        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), MY_CLUB_COUNT)

    def test_is_admin_true(self):
        """Tests club response if is_admin is True"""

        MY_CLUB_COUNT = 3

        ClubService(self.clubs[0]).add_member(self.user, roles=["President"])
        ClubService(self.clubs[1]).add_member(self.user, roles=["Member"])
        ClubService(self.clubs[2]).add_member(self.user, roles=["Member"])

        url = club_list_url_member(is_admin=True)

        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), MY_CLUB_COUNT)

    def test_is_admin_false(self):
        """Tests club response if is_admin is False"""

        MY_CLUB_COUNT = 3

        ClubService(self.clubs[0]).add_member(self.user, roles=["President"])
        ClubService(self.clubs[1]).add_member(self.user, roles=["Member"])
        ClubService(self.clubs[2]).add_member(self.user, roles=["Member"])

        url = club_list_url_member(is_admin=False)

        res = self.client.get(url)

        self.assertResOk(res)
        data = res.json()

        self.assertEqual(len(data), MY_CLUB_COUNT)


class SingleClubApiPermsTests(PublicApiTestsBase):
    """Testing perms for a user within a single club."""

    def setUp(self):
        super().setUp()

        self.club = create_test_club()
        self.user = create_test_user()
        self.client.force_authenticate(self.user)

    def test_creating_membership(self):
        """Should now allow creating a membership with an elavated role."""

        url = club_members_list_url(self.club.pk)
        payload = {
            "user": {
                "email": self.user.email,
            },
            "roles": ["President"],
        }

        res = self.client.post(url, data=payload)
        self.assertResNotFound(res)

        self.assertEqual(self.club.memberships.count(), 0)

    def test_change_own_role_viewer(self):
        """Should not be able to change own role within club unless admin."""

        # User is a member of the club
        mem = ClubService(self.club).add_member(self.user, roles=["Member"])

        # Then they try to set their own role
        url = club_members_detail_url(self.club.pk, mem.pk)
        payload = {
            "user": {
                "email": self.user.email,
            },
            "roles": ["President"],
        }

        res = self.client.post(url, data=payload)
        self.assertResForbidden(res)

        # Ensure their role didn't change
        mem.refresh_from_db()
        self.assertFalse(mem.roles.filter(name="President").exists())

    def test_change_own_role_editor(self):
        """Should not be able to change own role within club unless admin."""

        # User is a member of the club
        mem = ClubService(self.club).add_member(self.user, roles=["Officer"])

        # Then they try to set their own role
        url = club_members_detail_url(self.club.pk, mem.pk)
        payload = {
            "user": {
                "email": self.user.email,
            },
            "roles": ["President"],
        }

        res = self.client.post(url, data=payload)
        self.assertResForbidden(res)

        # Ensure their role didn't change
        mem.refresh_from_db()
        self.assertFalse(mem.roles.filter(name="President").exists())
