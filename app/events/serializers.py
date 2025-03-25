from clubs.models import Club
from core.abstracts.serializers import ModelSerializerBase
from events.models import Event, EventTag
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from rest_framework import serializers


class EventSerializer(ModelSerializerBase):
    class Meta:
        model = Event
        fields = [
            *ModelSerializerBase.default_fields,
            "name",
            "description",
            "location",
            "start_at",
            "end_at",
            "tags",
            "clubs",
            "primary_club",
            "attendance_links",
            "hosts",
            "all_day"
        ]


class EventCsvSerializer(CsvModelSerializer):
    """CSV Fields for events."""

    clubs = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Club.objects.all(),
        many=True,
        help_text="Club names",
    )
    tags = WritableSlugRelatedField(
        slug_field="name",
        queryset=EventTag.objects.all(),
        many=True,
        help_text="Tag names",
    )

    class Meta:
        model = Event
        fields = "__all__"
