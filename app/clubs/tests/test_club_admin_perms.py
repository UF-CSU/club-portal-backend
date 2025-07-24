import pytz
from django.utils import timezone

from clubs.models import ClubFile, ClubMembership, RoleType
from clubs.services import ClubService
from clubs.tests.utils import (
    club_detail_url,
    club_file_detail_url,
    club_file_list_url,
    club_members_detail_url,
    club_members_list_url,
    create_test_club,
    create_test_clubfile,
)
from core.abstracts.tests import PrivateApiTestsBase
from events.models import Event, RecurringEvent
from events.tests.utils import (
    EVENT_LIST_URL,
    RECURRINGEVENT_LIST_URL,
    create_test_event,
    event_detail_url,
)
from lib.faker import fake
from users.tests.utils import create_test_user
from utils.testing import create_test_uploadable_image


class ApiClubAdminTests(PrivateApiTestsBase):
    """
    Test club admin access to api.

    Each test ensures that the permissions do not bleed to
    other clubs.
    """

    def create_authenticated_user(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)

        self.other_club = create_test_club()
        self.other_service = ClubService(self.other_club)

        # Initialize owner user
        self.owner_user = create_test_user()
        self.owner_membership = self.service.add_member(
            self.owner_user, roles=["President"], is_owner=True
        )

        # Initialize main user
        user = create_test_user()
        self.membership = self.service.add_member(user, roles=["Officer"])

        # Initialize member user
        self.member_user = create_test_user()
        self.member_membership = self.service.add_member(
            self.member_user, roles=["Member"]
        )

        # Initialize other users
        self.other_owner = create_test_user()
        self.other_service.add_member(
            self.other_owner, roles=["President"], is_owner=True
        )

        self.other_user = create_test_user()
        self.other_user_membership = self.other_service.add_member(
            self.other_user, roles=["Member"]
        )

        # Default to officer for all tests
        return user

    def test_edit_club_info(self):
        """Admins should only be able to edit their club."""

        payload = {
            "name": self.club.name + " updated",
        }

        # Our club
        url = club_detail_url(self.club.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.club.refresh_from_db()
        self.assertEqual(self.club.name, payload["name"])

        # Other club
        url = club_detail_url(self.other_club.id)
        payload["name"] += " 2"
        res = self.client.patch(url, payload)
        self.assertResNotFound(res)
        self.assertNotEqual(self.other_club.name, payload["name"])

    def test_add_club_files(self):
        """Admins should be able to add club files."""

        file_count_before = ClubFile.objects.count()

        # Our club
        payload = {"file": create_test_uploadable_image()}
        url = club_file_list_url(self.club.id)
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        self.assertEqual(ClubFile.objects.count(), file_count_before + 1)
        file_count_before += 1

        # Other club
        payload = {"file": create_test_uploadable_image()}
        url = club_file_list_url(self.other_club.id)
        res = self.client.post(url, payload)
        self.assertResNotFound(res)

        self.assertEqual(ClubFile.objects.count(), file_count_before)

    def test_delete_club_files(self):
        """Admins should be able to delete club files."""

        # Our club
        club_file = create_test_clubfile(self.club)
        file_count_before = ClubFile.objects.count()

        url = club_file_detail_url(self.club.id, club_file.pk)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertEqual(ClubFile.objects.count(), file_count_before - 1)

        # Other club
        other_club_file = create_test_clubfile(self.other_club)
        file_count_before = ClubFile.objects.count()

        url = club_file_detail_url(self.other_club.id, other_club_file.id)
        res = self.client.delete(url)
        self.assertResNotFound(res)

        self.assertEqual(ClubFile.objects.count(), file_count_before)

    def test_add_club_events(self):
        """Admins should be able to add club events."""

        payload = {
            "name": fake.title(),
            "description": fake.paragraph(),
            "location": fake.address(),
            "event_type": "gbm",
            "start_at": timezone.datetime(
                year=2025,
                month=7,
                day=23,
                hour=17,
                minute=0,
                tzinfo=pytz.timezone("US/Eastern"),
            ),
            "end_at": timezone.datetime(
                year=2025,
                month=7,
                day=23,
                hour=19,
                minute=0,
                tzinfo=pytz.timezone("US/Eastern"),
            ),
            "hosts": [],
        }

        # Our club
        payload["hosts"] = [{"club_id": self.club.id, "is_primary": True}]
        url = EVENT_LIST_URL
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.for_club(self.club).count(), 1)

        # Other club
        payload["name"] += " copy"
        payload["hosts"] = [{"club_id": self.other_club.id, "is_primary": True}]
        url = EVENT_LIST_URL
        res = self.client.post(url, payload, format="json")
        self.assertResForbidden(res)

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.for_club(self.other_club).count(), 0)

        # No hosts
        payload["name"] += " copy"
        payload["hosts"] = []
        url = EVENT_LIST_URL
        res = self.client.post(url, payload, format="json")
        self.assertResForbidden(res)

        self.assertEqual(Event.objects.count(), 1)

        # Only secondary hosts
        payload["name"] += " copy"
        payload["hosts"] = [{"club_id": self.club.id, "is_primary": False}]
        url = EVENT_LIST_URL
        res = self.client.post(url, payload, format="json")
        self.assertResBadRequest(res)

        self.assertEqual(Event.objects.count(), 1)

    def test_edit_hosted_events(self):
        """Admins should only be able to edit events where their club is a host."""

        payload = {
            "name": fake.title(),
        }

        e0 = create_test_event(host=self.club)
        e1 = create_test_event(host=self.club, secondary_hosts=[self.other_club])
        e2 = create_test_event(host=self.other_club, secondary_hosts=[self.club])
        e3 = create_test_event(host=self.other_club)

        # E0: Is main host, can edit
        url = event_detail_url(e0.id)
        payload["name"] = fake.title() + " 0"
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        e0.refresh_from_db()
        self.assertEqual(e0.name, payload["name"])

        # E1: Is main host, has secondary host, can edit
        url = event_detail_url(e1.id)
        payload["name"] = fake.title() + " 1"
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        e1.refresh_from_db()
        self.assertEqual(e1.name, payload["name"])

        # E2: Is secondary host, can edit
        url = event_detail_url(e2.id)
        payload["name"] = fake.title() + " 2"
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        e2.refresh_from_db()
        self.assertEqual(e2.name, payload["name"])

        # E3: Is not host, cannot edit
        url = event_detail_url(e3.id)
        payload["name"] = fake.title() + " 3"
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        e3.refresh_from_db()
        self.assertNotEqual(e3.name, payload["name"])

    def test_delete_club_events(self):
        """Admins should be able to delete club events."""

        e0 = create_test_event(host=self.club)
        e1 = create_test_event(host=self.club, secondary_hosts=[self.other_club])
        e2 = create_test_event(host=self.other_club, secondary_hosts=[self.club])
        e3 = create_test_event(host=self.other_club)

        # E0: Is main host, can delete
        url = event_detail_url(e0.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(Event.objects.filter(id=e0.pk).exists())

        # E1: Is main host, has secondary host, can delete
        url = event_detail_url(e1.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(Event.objects.filter(id=e1.pk).exists())

        # E2: Is secondary host, can delete
        url = event_detail_url(e2.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(Event.objects.filter(id=e2.pk).exists())

        # E3: Is not host, cannot delete
        url = event_detail_url(e3.id)
        res = self.client.delete(url)
        self.assertResForbidden(res)

        self.assertTrue(Event.objects.filter(id=e3.pk).exists())

    def test_add_recurring_events(self):
        """Admins should be able to add recurring events."""

        payload = {
            "name": fake.title(),
            "event_type": "gbm",
            "days": [0],
            "event_start_time": "17:00",
            "event_end_time": "19:00",
            "start_date": "2025-07-01",
            "end_date": "2025-07-23",
        }

        # Is host, is allowed
        self.assertFalse(Event.objects.for_club(self.club).exists())

        payload["club"] = self.club.id

        url = RECURRINGEVENT_LIST_URL
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        rec_query = RecurringEvent.objects.filter(club=self.club)
        self.assertTrue(rec_query.exists())
        self.assertTrue(Event.objects.for_club(self.club).exists())

        rec_query.delete()

        # Is host, has secondary, is allowed
        self.assertFalse(Event.objects.for_club(self.club).exists())

        payload["club"] = self.club.id
        payload["other_clubs"] = [self.other_club.id]

        url = RECURRINGEVENT_LIST_URL
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        rec_query = RecurringEvent.objects.filter(club=self.club)
        self.assertTrue(rec_query.exists())

        self.assertTrue(Event.objects.for_club(self.club).exists())
        self.assertTrue(Event.objects.for_club(self.other_club).exists())

        rec_query.delete()

        # Is not host, is secondary, is allowed
        self.assertFalse(Event.objects.for_club(self.club).exists())

        payload["club"] = self.other_club.id
        payload["other_clubs"] = [self.club.id]

        url = RECURRINGEVENT_LIST_URL
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        rec_query_host = RecurringEvent.objects.filter(club=self.other_club)
        rec_query_other_host = RecurringEvent.objects.filter(
            other_clubs__id=self.club.id
        )

        self.assertTrue(rec_query_host.exists())
        self.assertTrue(rec_query_other_host.exists())

        self.assertFalse(RecurringEvent.objects.filter(club=self.club).exists())
        self.assertFalse(
            RecurringEvent.objects.filter(other_clubs__id=self.other_club.id).exists()
        )

        rec_query_host.delete()
        rec_query_other_host.delete()

        # Is not host, is not allowed
        self.assertFalse(Event.objects.for_club(self.club).exists())

        payload["club"] = self.club.id
        payload["other_clubs"] = [self.other_club.id]

        url = RECURRINGEVENT_LIST_URL
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        rec_query = RecurringEvent.objects.filter(club=self.club)
        self.assertTrue(rec_query.exists())
        self.assertTrue(Event.objects.for_club(self.club).exists())
        self.assertTrue(Event.objects.for_club(self.other_club).exists())

        rec_query.delete()

        # Is not host, is secondary, is not allowed
        self.assertFalse(Event.objects.for_club(self.club).exists())

        payload["club"] = self.other_club.id

        url = RECURRINGEVENT_LIST_URL
        res = self.client.post(url, payload)
        self.assertResForbidden(res)

        rec_query = RecurringEvent.objects.filter(club=self.club)
        self.assertFalse(rec_query.exists())
        rec_query = RecurringEvent.objects.filter(other_clubs__id=self.club.id)
        self.assertFalse(rec_query.exists())
        self.assertFalse(Event.objects.for_club(self.club).exists())

    def test_add_members(self):
        """Admins should be able to add club members."""

        payload = {
            "user": {
                "email": fake.safe_email(),
                "send_account_email": False,
            },
            "send_email": False,
            "roles": ["Officer"],
        }
        initial_member_count = self.club.member_count

        # Our club
        url = club_members_list_url(self.club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        self.assertEqual(self.club.member_count, initial_member_count + 1)
        membership = ClubMembership.objects.get(
            club=self.club, user__email=payload["user"]["email"]
        )
        self.assertEqual(membership.is_admin, True)

        # Other club
        url = club_members_list_url(self.other_club.id)
        res = self.client.post(url, payload, format="json")
        self.assertResNotFound(res)

        self.assertFalse(
            ClubMembership.objects.filter(
                club=self.other_club, user__email=payload["user"]["email"]
            )
        )

    def test_unable_set_owner(self):
        """Admin should not be able to set an owner if they are not owner."""

        payload = {
            "is_owner": True,
        }

        # Our club, set self as owner
        url = club_members_detail_url(self.club.id, self.membership.id)
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        self.membership.refresh_from_db()
        self.assertFalse(self.membership.is_owner)

        # Our club, set other user as owner
        url = club_members_detail_url(self.club.id, self.member_membership.id)
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        self.member_membership.refresh_from_db()
        self.assertFalse(self.member_membership.is_owner)

        # Other club
        url = club_members_detail_url(self.club.id, self.other_user_membership.id)
        res = self.client.patch(url, payload)
        self.assertResNotFound(res)

        self.other_user_membership.refresh_from_db()
        self.assertFalse(self.other_user_membership.is_owner)

        # Our club, change owner's ownership
        payload["is_owner"] = False
        url = club_members_detail_url(self.club.id, self.owner_membership.id)
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        self.owner_membership.refresh_from_db()
        self.assertTrue(self.owner_membership.is_owner)

    def test_owner_set_other_owner(self):
        """Admin who is an owner should be able to set another owner."""

        # Proceed as the owner
        self.client.force_authenticate(self.owner_user)

        # Cannot unset self as owner
        payload = {"is_owner": False}
        url = club_members_detail_url(self.club.id, self.owner_membership.id)
        res = self.client.patch(url, payload)
        self.assertResBadRequest(res)

        self.owner_membership.refresh_from_db()
        self.assertTrue(self.owner_membership.is_owner)

        # Can set other user as owner
        payload = {"is_owner": True}
        url = club_members_detail_url(self.club.id, self.membership.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_owner)

        self.owner_membership.refresh_from_db()
        self.assertFalse(self.owner_membership.is_owner)

        # Owner of 1 club, member of another
        self.other_service.add_member(self.owner_user, roles=["Member"])
        payload = {"is_owner": True}
        url = club_members_detail_url(self.other_club.id, self.other_user_membership.pk)
        res = self.client.patch(url, payload)
        self.assertResForbidden(res)

        self.other_user_membership.refresh_from_db()
        self.assertFalse(self.other_user_membership.is_owner)

    def test_edit_member_roles(self):
        """Admins should be able to edit member roles."""

        # Our club, change other member
        payload = {"roles": ["Officer"]}
        url = club_members_detail_url(self.club.id, self.member_membership.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.assertTrue(self.member_membership.roles.filter(name="Officer").exists())
        self.assertTrue(self.member_membership.is_admin)

        # Our club, change owner
        payload = {"roles": ["Member"]}
        url = club_members_detail_url(self.club.id, self.owner_membership.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.owner_membership.refresh_from_db()
        self.assertFalse(self.owner_membership.roles.filter(name="President").exists())
        self.assertTrue(self.owner_membership.is_owner)
        self.assertTrue(self.owner_membership.is_admin)

        # Other club
        other_member = create_test_user()
        other_member_membership = self.other_service.add_member(
            other_member, roles=["Member"]
        )
        payload = {"roles": ["Officer"]}

        url = club_members_detail_url(self.other_club.id, other_member_membership.id)
        res = self.client.patch(url, payload)
        self.assertResNotFound(res)

        self.assertFalse(other_member_membership.roles.filter(name="Officer").exists())

        # Our club, change self (downgrade self to member)
        payload = {"roles": ["Member"]}
        url = club_members_detail_url(self.club.id, self.membership.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.membership.refresh_from_db()
        self.assertFalse(self.membership.roles.filter(name="Officer").exists())
        self.assertFalse(
            self.membership.roles.filter(role_type=RoleType.ADMIN).exists()
        )
        self.assertFalse(self.membership.is_admin)

    def test_remove_members(self):
        """Admins should be able to remove members, including other owners."""

        # Our club, other user
        url = club_members_detail_url(self.club.id, self.member_membership.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(
            ClubMembership.objects.filter(
                club=self.club, user=self.member_user
            ).exists()
        )

        # Our club, owner
        url = club_members_detail_url(self.club.id, self.owner_membership.id)
        res = self.client.delete(url)
        self.assertResBadRequest(res)

        self.assertTrue(
            ClubMembership.objects.filter(club=self.club, user=self.owner_user).exists()
        )
        # Other club
        url = club_members_detail_url(self.club.id, self.other_user_membership.id)
        res = self.client.delete(url)
        self.assertResNotFound(res)

        self.assertTrue(
            ClubMembership.objects.filter(
                club=self.other_club, user=self.other_user
            ).exists()
        )

        # Our club, self
        url = club_members_detail_url(self.club.id, self.membership.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(
            ClubMembership.objects.filter(club=self.club, user=self.user).exists()
        )
