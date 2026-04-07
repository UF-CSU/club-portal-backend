from clubs.services import ClubService
from core.abstracts.models import RoleType
from core.abstracts.tests import EmailTestsBase, PrivateApiTestsBase
from django.urls import reverse

from clubs.models import Club, Team, TeamMembership, TeamRole
from clubs.tests.utils import create_test_club, create_test_clubs, create_test_team
from lib.faker import fake
from users.tests.utils import create_test_user


def teams_list_url(club_id):
    return reverse("api-clubs:team-list", kwargs={"club_id": club_id})

def team_invite_url(club_id: int, team_id: int):
    return reverse("api-clubs:teaminvite", args=[club_id, team_id])

def team_members_list_url(club_id: int, team_id: int):
    return reverse("api-clubs:teammember-list", args=[club_id, team_id])

def team_members_detail_url(club_id: int, team_id: int, member_id: int):
    return reverse("api-clubs:teammember-detail", args=[club_id, team_id, member_id])


class TeamPrivateApiTests(PrivateApiTestsBase, EmailTestsBase):
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

    def test_send_team_email_invites_api(self):
        """Should be able to send team email invites via the API."""

        email_count = 5

        club = create_test_club()
        team = create_test_team(club)

        url = team_invite_url(club.id, team.id)
        payload = {"emails": [fake.safe_email() for _ in range(email_count)]}

        res = self.client.post(url, payload, format=None)
        self.assertResAccepted(res)
        self.assertEmailsSent(email_count)


class ApiTeamAdminTests(PrivateApiTestsBase):
    """
    Test team admin access to api.

    Each test ensures that the permissions do not bleed to
    other teams.
    """
    def create_authenticated_user(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)
        self.team = create_test_team(self.club)

        self.team_role = TeamRole.objects.create(
            team=self.team, name="Other"
        )

        self.other_club = create_test_club()
        self.other_service = ClubService(self.other_club)
        self.other_team = create_test_team(self.club)

        # Initialize main user
        user = create_test_user()
        self.club_membership = self.service.add_member(user, roles=["Vice-President"])
        self.team_membership = self.service.add_team_member(user, self.team, roles=["Admin"])

        # Initialize member user
        self.member_user = create_test_user()
        self.member_membership = self.service.add_team_member(
            self.member_user, self.team, roles=["Member"]
        )

        # Initialize other users
        self.other_user = create_test_user()
        self.other_user_membership = self.other_service.add_team_member(
            self.other_user, self.other_team, roles=["Member"]
        )

        return user

    def test_add_members(self):
        """Admins should be able to add team members."""

        payload = {
            "user": {
                "email": fake.safe_email(),
                "send_account_email": False,
            },
            "send_email": False,
            "roles": ["Member"],
        }
        initial_member_count = TeamMembership.objects.filter(team=self.team).count()

        # Our team
        url = team_members_list_url(self.club.id, self.team.id)
        res = self.client.post(url, payload, format="json")
        self.assertResCreated(res)

        self.assertEqual(
            TeamMembership.objects.filter(team=self.team).count(),
            initial_member_count + 1,
        )
        membership = TeamMembership.objects.get(
            team=self.team, user__email=payload["user"]["email"]
        )
        self.assertTrue(membership.roles.filter(name="Member").exists())

        # Other team
        url = team_members_list_url(self.other_club.id, self.other_team.id)
        res = self.client.post(url, payload, format="json")
        self.assertResNotFound(res)

        self.assertFalse(
            TeamMembership.objects.filter(
                team=self.other_team, user__email=payload["user"]["email"]
            )
        )

    def test_edit_member_roles(self):
        """Admins should be able to edit member roles."""

        # Our club, change other member
        payload = {"roles": ["Other"]}
        url = team_members_detail_url(self.club.id, self.team.id, self.member_membership.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.assertTrue(
            self.member_membership.roles.filter(name="Other").exists()
        )

        # Other club
        payload = {"roles": ["Admin"]}

        url = team_members_detail_url(self.other_club.id, self.other_team.id, self.other_user_membership.id)
        res = self.client.patch(url, payload)
        self.assertResNotFound(res)

        self.assertFalse(
            self.other_user_membership.roles.filter(name="Admin").exists()
        )

        # Our club, change self (downgrade self to member)
        payload = {"roles": ["Member"]}
        url = team_members_detail_url(self.club.id, self.team.id, self.team_membership.id)
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        self.team_membership.refresh_from_db()
        self.assertFalse(self.team_membership.roles.filter(name="Admin").exists())
        self.assertFalse(
            self.team_membership.roles.filter(role_type=RoleType.ADMIN).exists()
        )
        self.assertFalse(self.team_membership.is_admin)

    def test_remove_members(self):
        """Admins should be able to remove members, including other owners."""

        # Our club, other user
        url = team_members_detail_url(self.club.id, self.team.id, self.member_membership.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(
            TeamMembership.objects.filter(
                team=self.team, user=self.member_user
            ).exists()
        )

        # Other club
        url = team_members_detail_url(self.other_club.id, self.other_team.id, self.other_user_membership.id)
        res = self.client.delete(url)
        self.assertResNotFound(res)

        self.assertTrue(
            TeamMembership.objects.filter(
                team=self.other_team, user=self.other_user
            ).exists()
        )

        # Our club, self
        url = team_members_detail_url(self.club.id, self.team.id, self.team_membership.id)
        res = self.client.delete(url)
        self.assertResNoContent(res)

        self.assertFalse(
            TeamMembership.objects.filter(team=self.team, user=self.user).exists()
        )