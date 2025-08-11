from core.models import Major
from querycsv.serializers import CsvModelSerializer


class MajorCsvSerializer(CsvModelSerializer):
    """Determine major fields for a csv."""

    class Meta:
        model = Major
        fields = "__all__"
