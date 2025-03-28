from core.mock.models import Buster, BusterTag
from lib.faker import fake


def create_test_buster(**kwargs):
    """Create mock dummy object for testing."""

    payload = {"name": fake.title(3), **kwargs}

    return Buster.objects.create(**payload)


def create_test_buster_tag(**kwargs):
    """Create mock tag for dummy object."""

    payload = {"name": fake.title(3), **kwargs}

    return BusterTag.objects.create(**payload)


def create_test_busters(count=3, **kwargs):
    """Create multiple dummy objects for testing."""

    buster_ids = []
    for _ in range(count):
        buster_ids.append(create_test_buster(**kwargs).pk)

    return Buster.objects.filter(id__in=buster_ids)
