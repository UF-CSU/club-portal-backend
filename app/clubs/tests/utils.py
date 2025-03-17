import uuid

from django.urls import reverse

from clubs.models import Club, Team
from lib.faker import fake

CLUB_CREATE_PARAMS = {
    "name": "Test Club",
}
CLUB_UPDATE_PARAMS = {"name": "Updated Club"}


def create_test_club(name=None, **kwargs):
    """Create unique club for unit tests."""
    if name is None:
        name = f"Test Club {uuid.uuid4()}"

    alias = kwargs.pop("alias", None)
    while not alias:
        new_alias = "".join(fake.random_letters(5))

        if Club.objects.filter(alias__iexact=new_alias).exists():
            continue

        alias = new_alias

    return Club.objects.create(name=name, alias=alias, **kwargs)


def create_test_clubs(count=5, **kwargs):
    """Create amount of clubs equal to count, returns queryset."""

    ids = [create_test_club(**kwargs).id for _ in range(count)]
    return Club.objects.filter(id__in=ids).all()


def create_test_team(club: Club, **kwargs):
    """Create valid team for unit tests."""

    payload = {"name": kwargs.pop("name", f"Team {uuid.uuid4()}"), **kwargs}

    return Team.objects.create(club=club, **payload)


def join_club_url(club_id: int):
    return reverse("clubs:join", kwargs={"club_id": club_id})


def club_home_url(club_id: int):
    return reverse("clubs:home", kwargs={"club_id": club_id})
