from rest_framework import serializers

from clubs.models import Club
from core.abstracts.serializers import ModelSerializerBase
from events.models import Event, EventAttendance, EventCancellation, EventHost, EventTag
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from users.models import User


class EventTagSerializer(ModelSerializerBase):
    """Group related events."""

    # TODO: This shows as readonly in typegen, shouldn't be readonly
    id = serializers.PrimaryKeyRelatedField(queryset=EventTag.objects.all())

    class Meta:
        model = EventTag
        fields = ["id", "name", "color", "order"]
        read_only_fields = ["name", "color", "order"]


class EventHostSerializer(ModelSerializerBase):
    """JSON representation for hosts inside events."""

    club_id = serializers.PrimaryKeyRelatedField(
        source="club", queryset=Club.objects.all()
    )
    club_name = serializers.SlugRelatedField(
        source="club", read_only=True, slug_field="name"
    )
    club_logo = serializers.ImageField(
        source="club.logo", read_only=True, required=False, allow_null=True
    )

    class Meta:
        model = EventHost
        fields = ["id", "club_id", "club_name", "club_logo", "is_primary"]
        read_only_fields = [
            "id",
            "club_name",
            "club_logo",
        ]
        # required_fields_update = ["id"]


class EventSerializer(ModelSerializerBase):
    """Represents a calendar event for a single or multiple clubs."""

    hosts = EventHostSerializer(many=True, required=False)
    all_day = serializers.BooleanField(read_only=True)
    tags = EventTagSerializer(many=True, required=False)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "description",
            "location",
            "event_type",
            "start_at",
            "end_at",
            "tags",
            "hosts",
            "all_day",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        hosts_data = validated_data.pop("hosts", [])

        event = Event.objects.create(**validated_data)

        for host in hosts_data:

            EventHost.objects.create(
                event=event, club=host["club"], is_primary=host.get("is_primary", False)
            )

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


class EventAttendanceCsvSerializer(CsvModelSerializer):
    event = None
    name = serializers.CharField(
        write_only=True, max_length=128, help_text="Name of event"
    )
    start_at = serializers.DateTimeField(
        write_only=True, help_text="Start datetime of event"
    )
    end_at = serializers.DateTimeField(
        write_only=True, help_text="End datetime of event"
    )

    user = WritableSlugRelatedField(
        slug_field="email",
        queryset=User.objects.all(),
        help_text="Email of attendee",
    )

    class Meta:
        model = EventAttendance
        exclude = ("event",)

    def validate(self, attrs):
        name = attrs.get("name")
        start_at = attrs.get("start_at")
        end_at = attrs.get("end_at")

        try:
            event = Event.objects.get(
                name=name,
                start_at=start_at,
                end_at=end_at,
            )
        except Event.DoesNotExist:
            raise serializers.ValidationError(
                "Event with the given name, start_at and end_at does not exist."
            )

        attrs["event"] = event
        return attrs

    def create(self, validated_data):
        validated_data.pop("name", None)
        validated_data.pop("start_at", None)
        validated_data.pop("end_at", None)
        return super().create(validated_data)


class EventCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCancellation
        fields = "__all__"
