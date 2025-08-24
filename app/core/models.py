from django.db import models

from core.abstracts.models import ModelBase


class Major(ModelBase):
    """Academic major."""

    name = models.CharField(max_length=64, unique=True)
