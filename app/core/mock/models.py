import uuid

from django.db import models

from core.abstracts.models import ModelBase


class BusterTag(ModelBase):
    """Dummy related model used for testing only."""

    name = models.CharField(max_length=64)
    color = models.CharField(null=True, blank=True)


class Buster(ModelBase):
    """
    Dummy model used for testing only.
    This allows core tests to not be reliant on models from other apps.
    """

    name = models.CharField()
    unique_name = models.CharField(unique=True, default=uuid.uuid4)
    one_tag = models.ForeignKey(
        BusterTag, on_delete=models.SET_NULL, null=True, blank=True
    )
    many_tags = models.ManyToManyField(BusterTag, blank=True, related_name="busters")
