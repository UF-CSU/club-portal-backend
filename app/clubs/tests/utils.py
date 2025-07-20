import uuid
from typing import Optional

from django.urls import reverse

from clubs.models import Club, Team, TeamRole
from clubs.services import ClubService
from lib.faker import fake
from users.models import User

CLUB_CREATE_PARAMS = {
    "name": "Test Club",
}
CLUB_UPDATE_PARAMS = {"name": "Updated Club"}


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
