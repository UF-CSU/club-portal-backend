from rest_framework import serializers

from clubs.models import Club
from core.abstracts.serializers import ModelSerializerBase
from events.models import Event, EventCancellation, EventHost, EventTag
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField


class EventHostNestedSerializer(ModelSerializerBase):
    """JSON representation for hosts inside events."""

    class Meta:
        model = EventHost
        fields = ["club", "primary"]


class EventSerializer(ModelSerializerBase):
    """Represents a calendar event for a single or multiple clubs."""

    hosts = EventHostNestedSerializer(many=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "description",
            "location",
            "start_date",
            "end_date",
            "start_at",
            "end_at",
            "tags",
            "attendance_links",
            "hosts",
            "all_day",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        hosts_data = validated_data.pop('hosts', [])
        attendance_links_data = validated_data.pop('attendance_links', [])

        event = Event.objects.create(**validated_data)

        for host in hosts_data:
            EventHost.objects.create(
                event=event,
                club=host['club'],
                primary=host.get('primary', False)
            )

        event.attendance_links.set(attendance_links_data)

        return event
        


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


class EventCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCancellation
        fields = "__all__"
