from querycsv.serializers import CsvModelSerializer

from core.models import Major


class MajorCsvSerializer(CsvModelSerializer):
    """Determine major fields for a csv."""

    class Meta:
        model = Major
        fields = "__all__"
