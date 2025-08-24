from django.contrib import admin

from core.abstracts.admin import ModelAdminBase
from core.models import Major
from core.serializers import MajorCsvSerializer


class MajorAdmin(ModelAdminBase):
    """Manage majors in admin."""

    csv_serializer_class = MajorCsvSerializer


admin.site.register(Major, MajorAdmin)
