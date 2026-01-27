from core.abstracts.tests import EmailTestsBase, PrivateApiTestsBase, PublicApiTestsBase
from django.forms import forms
from django.http import HttpResponse
from django.urls import reverse
from rest_framework import status
from users.models import User
from users.tests.utils import create_test_user

from clubs.services import ClubService
from clubs.tests.utils import create_test_club

INVITE_CLUB_ADMIN_URL = reverse("core:invite_club_admin")


class PublicClubViewTests(PublicApiTestsBase):
    """Unit tests with unauthenticated users for club views."""

    def test_only_staff_see_invite_form(self):
        """Should raise permissions error if trying to view invite form."""

        url = INVITE_CLUB_ADMIN_URL

        # As unauthenticated user
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        # As non-staff user
        user = create_test_user()
        self.client.force_login(user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        # Finally, as staff
        user.is_staff = True
        user.save()
        res = self.client.get(url)
        self.assertResOk(res)


class PrivateClubViewTests(PrivateApiTestsBase, EmailTestsBase):
    """Unit tests with authenticated user for club views."""

    def _get_form_from_res(self, res: HttpResponse) -> forms.Form:
        """Extract form object from response."""

        return res.context.get("form")

    def assertFormHasErrors(self, res: HttpResponse):
        """Form in response should have errors."""

        form = self._get_form_from_res(res)
        self.assertFalse(form.is_valid(), "Form is unexpectedly valid")

    def assertFormIsValid(self, res: HttpResponse):
        """Form in response should have been submitted successfully."""

        form = self._get_form_from_res(res)
        self.assertTrue(not form.is_bound or form.is_valid(), form.errors.as_data())

    def create_authenticated_user(self):
        user = super().create_authenticated_user()

        # Allow user to see invite forms
        user.is_staff = True
        user.save()

        return user

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)

    def test_invite_club_admin(self):
        """Should send invite email to club admin."""

        # Target user/club
        u2 = create_test_user()
        club = create_test_club()

        # Submit form
        payload = {
            "email": u2.email,
            "club": club.id,
            "is_owner": True,
            "send_invite": True,
        }

        res: HttpResponse = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormIsValid(res)

        # Verify membership, invite sent
        self.assertTrue(club.memberships.filter(user__id=u2.id, is_owner=True).exists())
        self.assertEmailsSent(1)

    def test_invite_club_admin_create_user(self):
        """Should create user if needed when inviting admin."""

        self.assertIsNone(User.objects.find_by_email("user@example.com"))
        club = create_test_club()

        # Submit form
        payload = {
            "email": "user@example.com",
            "club": club.id,
            "is_owner": True,
            "send_invite": True,
        }
        res = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormIsValid(res)

        # Verify user created and added to club
        user = User.objects.find_by_email("user@example.com")
        self.assertIsNotNone(user)
        self.assertTrue(user.clubs.filter(id=club.id).exists())
        self.assertTrue(user.club_memberships.get(club__id=club.id).is_admin)
        self.assertEmailsSent(2)  # User account setup, club invite email

    def test_invite_club_admin_create_user_no_invite_email(self):
        """Should send account setup link, but not club invite email."""

        self.assertIsNone(User.objects.find_by_email("user@example.com"))
        club = create_test_club()

        # Submit form
        payload = {
            "email": "user@example.com",
            "club": club.id,
            "is_owner": True,
            "send_invite": False,
        }
        res = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormIsValid(res)

        # Verify user created and added to club
        user = User.objects.find_by_email("user@example.com")
        self.assertIsNotNone(user)
        self.assertTrue(user.clubs.filter(id=club.id).exists())
        self.assertTrue(user.club_memberships.get(club__id=club.id).is_admin)
        self.assertEmailsSent(1)  # Just user account setup

    def test_invite_club_admin_not_owner(self):
        """Should add member to club and set as member if owner is disabled."""

        u2 = create_test_user()
        club = create_test_club()

        # Submit form
        payload = {
            "email": u2.email,
            "club": club.id,
            "is_owner": False,
            "send_invite": True,
        }
        res = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormIsValid(res)

        # Verify user added to club as member
        self.assertTrue(u2.clubs.filter(id=club.id).exists())
        self.assertFalse(u2.club_memberships.get(club__id=club.id).is_admin)
        self.assertEmailsSent(1)

    def test_invite_club_admin_change_owner(self):
        """Should set new user as owner and unset old owner."""

        # Target user/club
        u2 = create_test_user()
        u3 = create_test_user()
        club = create_test_club()

        ClubService(club).add_member(u3, is_owner=True)

        # Submit form
        payload = {
            "email": u2.email,
            "club": club.id,
            "is_owner": True,
            "send_invite": True,
        }

        res: HttpResponse = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormIsValid(res)

        # Verify membership, invite sent
        self.assertTrue(
            club.memberships.filter(user__id=u2.id, is_owner=True).exists()
        )  # U2 added
        self.assertTrue(club.memberships.filter(user__id=u3.id).exists())  # U3 stayed
        self.assertFalse(
            club.memberships.filter(user__id=u3.id, is_owner=True).exists()
        )  # U3 unassigned as owner
        self.assertEmailsSent(1)

    def test_invite_club_admin_not_send_email(self):
        """Should add user to club and not send email if disabled in form."""

        u2 = create_test_user()
        club = create_test_club()

        # Submit form
        payload = {
            "email": u2.email,
            "club": club.id,
            "is_owner": True,
            "send_invite": False,
        }
        res = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormIsValid(res)

        # Verify user added to club as member
        self.assertTrue(u2.clubs.filter(id=club.id).exists())
        self.assertTrue(u2.club_memberships.get(club__id=club.id).is_admin)
        self.assertEmailsSent(0)

    def test_invite_club_admin_already_in_club(self):
        """Should raise error if attempting to invite user already in club."""

        u2 = create_test_user()
        club = create_test_club()
        ClubService(club).add_member(u2)

        # Submit form
        payload = {
            "email": u2.email,
            "club": club.id,
            "is_owner": True,
            "send_invite": True,
        }
        res = self.client.post(INVITE_CLUB_ADMIN_URL, data=payload)
        self.assertResOk(res)
        self.assertFormHasErrors(res)

        # Verify user is member of club, but no emails sent
        self.assertTrue(u2.clubs.filter(id=club.id).exists())
        self.assertFalse(u2.club_memberships.get(club__id=club.id).is_admin)
        self.assertEmailsSent(0)
