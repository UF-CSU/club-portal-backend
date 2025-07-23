import uuid
from typing import Optional

from django.urls import reverse

from clubs.models import Club, ClubFile, ClubRole, RoleType, Team, TeamRole
from clubs.services import ClubService
from lib.faker import fake
from users.models import User
from utils.files import get_file_from_path
from utils.testing import create_test_image


def club_invite_url(club_id: int):
    return reverse("api-clubs:invite", args=[club_id])


def club_members_list_url(club_id: int):
    return reverse("api-clubs:clubmember-list", args=[club_id])


def club_members_detail_url(club_id: int, member_id: int):
    return reverse("api-clubs:clubmember-detail", args=[club_id, member_id])


def club_detail_url(club_id: int):
    return reverse("api-clubs:club-detail", args=[club_id])


def club_apikey_list_url(club_id: int):
    return reverse("api-clubs:apikey-list", args=[club_id])


CLUBS_LIST_URL = reverse("api-clubs:club-list")
CLUBS_JOIN_URL = reverse("api-clubs:join")


def club_list_url_member():
    return reverse("api-clubs:club-list")


def club_file_list_url(club_id: int):
    return reverse("api-clubs:file-list", args=[club_id])


def club_file_detail_url(club_id: int, file_id: int):
    return reverse("api-clubs:file-list", args=[club_id, file_id])


def create_test_clubfile(club: Club, **kwargs):
    """Create club file for testing."""

    payload = {
        "club": club,
        "file": get_file_from_path(create_test_image()),
    }

    return ClubFile.objects.create(**payload)


def create_test_club(name=None, members: Optional[list[User]] = None, **kwargs) -> Club:
    """Create unique club for unit tests."""
    if name is None:
        name = f"Test Club {uuid.uuid4()}"

    alias = kwargs.pop("alias", None)
    while not alias:
        new_alias = "".join(fake.random_letters(5))

        if Club.objects.filter(alias__iexact=new_alias).exists():
            continue

        alias = new_alias

    club = Club.objects.create(name=name, alias=alias, **kwargs)

    members = members or []
    svc = ClubService(club)

    for member in members:
        svc.add_member(member)

    return club


def create_test_clubrole(club: Club, role_type=RoleType.VIEWER, **kwargs):
    """Create viewer club role role for tests."""

    payload = {
        "name": " ".join(fake.words(2)),
        "default": False,
        **kwargs,
    }
    return ClubRole.objects.create(club=club, role_type=role_type, **payload)


def create_test_clubs(count=5, **kwargs):
    """Create amount of clubs equal to count, returns queryset."""

    ids = [create_test_club(**kwargs).id for _ in range(count)]
    return Club.objects.filter(id__in=ids).all()


def create_test_team(club: Club, clear_roles=False, **kwargs):
    """Create valid team for unit tests."""

    payload = {"name": kwargs.pop("name", f"Team {uuid.uuid4()}"), **kwargs}

    team = Team.objects.create(club=club, **payload)

    if clear_roles:
        TeamRole.objects.filter(team=team).delete()

    return team


def join_club_url(club_id: int):
    return reverse("clubs:join", kwargs={"club_id": club_id})


def club_home_url(club_id: int):
    return reverse("clubs:home", kwargs={"club_id": club_id})
