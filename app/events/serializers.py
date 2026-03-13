from clubs.models import Club
from clubs.serializers import ClubFileNestedSerializer
from core.abstracts.serializers import (
    ModelSerializerBase,
    RoundedDecimalField,
    SerializerBase,
)
from django.core import exceptions
from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema_serializer,
)
from polls.models import Poll
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from rest_framework import serializers
from users.models import User

from events.models import (
    Event,
    EventAttendance,
    EventAttendanceLink,
    EventCancellation,
    EventHost,
    EventTag,
    RecurringEvent,
)


class EventHostSerializer(ModelSerializerBase):
    """JSON representation for hosts inside events."""

    # TODO: Rename to "club" or change to serializers.IntegerField
    club_id = serializers.PrimaryKeyRelatedField(
        source="club", queryset=Club.objects.all()
    )
    club_name = serializers.CharField(read_only=True)
    club_alias = serializers.CharField(read_only=True)
    club_logo = serializers.ImageField(read_only=True, allow_null=True)

    class Meta:
        model = EventHost
        fields = ["id", "club_id", "club_name", "club_logo", "club_alias", "is_primary"]
        read_only_fields = [
            "id",
            "club_name",
            "club_logo",
            "club_alias",
        ]


class EventAttendanceLinkSerializer(ModelSerializerBase):
    """Represent attendance links for events."""

    qrcode_url = serializers.ImageField(
        source="qrcode.image", read_only=True, help_text="URL for the QRCode SVG"
    )

    class Meta:
        model = EventAttendanceLink
        fields = [
            "id",
            "url",
            "reference",
            "is_tracked",
            "display_name",
            "qrcode_url",
        ]


class EventPreviewSerializer(ModelSerializerBase):
    """Shows minimal fields for public events."""

    status = serializers.CharField(read_only=True)
    duration = serializers.CharField(read_only=True)
    is_all_day = serializers.BooleanField(read_only=True)
    hosts = EventHostSerializer(many=True, required=False)
    tags = WritableSlugRelatedField(
        slug_field="name",
        queryset=EventTag.objects.all(),
        many=True,
        help_text="Tag names",
        required=False,
    )

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "location",
            "description",
            "event_type",
            "status",
            "duration",
            "is_all_day",
            "hosts",
            "tags",
            "is_draft",
            "is_public",
            "primary_color",
            "text_color",
        ]


class EventSerializer(EventPreviewSerializer):
    """Represents a calendar event for a single or multiple clubs."""

    attachments = ClubFileNestedSerializer(many=True, required=False)
    # poll = EventPollField(queryset=Poll.objects.all(), required=False, allow_null=True)
    attendance_links = EventAttendanceLinkSerializer(many=True, required=False)
    poll = serializers.PrimaryKeyRelatedField(
        queryset=Poll.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Event
        fields = EventPreviewSerializer.Meta.fields + [
            "recurring_event",
            "attachments",
            "attendance_links",
            "enable_attendance",
            "poll",
            "make_public_at",
        ]

    def validate(self, attrs):
        # Ensure that there are not only secondary hosts
        hosts = attrs.get("hosts", None)

        if not self.instance:
            primary_hosts = [
                host for host in hosts if host.get("is_primary", False) is True
            ]

            if len(primary_hosts) == 0 and len(hosts) > 0:
                raise exceptions.ValidationError(
                    "Event with hosts must have a primary host."
                )

        return super().validate(attrs)

    def create(self, validated_data):
        poll = validated_data.pop("poll", None)
        hosts_data = validated_data.pop("hosts", [])
        attachment_data = validated_data.pop("attachments", [])

        # Manually create tags if necessary
        tags = validated_data.pop("tags", [])
        validated_tags = []
        for tag in tags:
            if isinstance(tag, EventTag):
                validated_tags.append(tag)
                continue

            if not EventTag.objects.filter(name=tag.name).exists():
                validated_tags.append(EventTag.objects.create(name=tag.name))

        hosts_payload = {"host": None, "secondary_hosts": []}
        for host in hosts_data:
            is_primary = host.get("is_primary", False)
            club = host["club"]

            if is_primary:
                hosts_payload["host"] = club
            else:
                hosts_payload["secondary_hosts"].append(club)

        event = Event.objects.create(**validated_data, **hosts_payload)

        if poll:
            event.poll = poll
            event.save()

        for attachment in attachment_data:
            attachment_id = attachment["id"]

            event.attachments.add(attachment_id)

        event.tags.set(validated_tags)

        return event

    def update(self, instance, validated_data):
        has_poll = "poll" in validated_data
        poll = validated_data.pop("poll", None)
        attachment_data = validated_data.pop("attachments", [])

        # Preserve enable_attendance value from validated_data if provided, otherwise keep original
        enable_attendance_provided = "enable_attendance" in validated_data
        new_enable_attendance = validated_data.get(
            "enable_attendance", instance.enable_attendance
        )

        # Temporarily disable enable_attendance to avoid side effects during update
        original_enable_attendance = instance.enable_attendance
        validated_data["enable_attendance"] = False
        event = super().update(instance, validated_data)

        if has_poll and event.poll != poll:
            event.poll = poll
        event.refresh_from_db()

        # Apply the intended enable_attendance value if it was provided in the request
        if enable_attendance_provided:
            event.enable_attendance = new_enable_attendance
        # If not provided, maintain the original value
        else:
            event.enable_attendance = original_enable_attendance

        event.save()

        event.attachments.clear()

        for attachment in attachment_data:
            attachment_id = attachment["id"]
            event.attachments.add(attachment_id)

        return event


class PreviousEventAnalyticsNestedSerializer(SerializerBase):
    """Metrics of current event compared to previous event (for recurring events only)."""

    id = serializers.IntegerField(source="prev_id", help_text="Previous event ID")
    users_total = serializers.IntegerField(
        source="prev_users_total",
        help_text="Total distinct users that attended the previous event",
    )
    users_diff = RoundedDecimalField(
        source="prev_users_diff",
        help_text="Difference between number of users who attended the selected event and the previous event",
    )
    members_total = serializers.IntegerField(
        source="prev_members_total",
        help_text="Number of users who attended the previous event who were also members of the club",
    )
    members_diff = RoundedDecimalField(
        source="prev_members_diff",
        help_text="Difference between the members who attended the selected event and the previous event",
    )
    returning_total = serializers.IntegerField(
        source="prev_returning_total",
        help_text="Number of users who attended the previous event that also attended an earlier event",
    )
    returning_diff = RoundedDecimalField(
        source="prev_returning_diff",
        help_text="Difference between the returning users for the selected event and the previous event",
    )


class EventTypeAnalyticsNestedSerializer(SerializerBase):
    """Metrics of current event compared to all events for the primary club in the same event type."""

    events_count = serializers.IntegerField(
        source="evtype_events_count",
        help_text="Number of previous events for the primary club that had this event type",
    )
    users_avg = RoundedDecimalField(
        source="evtype_users_avg",
        help_text="Average number of users who attended the previous events with the same event type",
    )
    users_diff = RoundedDecimalField(
        source="evtype_users_diff",
        help_text="Difference between number of users who attended selected event and the average for the event type",
    )
    members_avg = RoundedDecimalField(
        source="evtype_members_avg",
        help_text="Average number of users who attended the previous events with the same event type that were also members of the primary club",
    )
    members_diff = RoundedDecimalField(
        source="evtype_members_diff",
        help_text="Difference between the total members for the selected event and the average number of members for the event type",
    )
    returning_avg = RoundedDecimalField(
        source="evtype_returning_avg",
        help_text="Average number of users for each event in the event type that had attended an event prior for the primary club",
    )
    returning_diff = RoundedDecimalField(
        source="evtype_returning_diff",
        help_text="Difference between the returning users for the selected event and the average returning users for the event type",
    )


class RecurringEventAnalyticsNestedSerializer(SerializerBase):
    """Metrics of current event compared to all events for the primary club in the same event type."""

    id = serializers.IntegerField(
        source="rec_id",
        help_text="ID of the recurring event attached to the selected event",
    )
    events_count = serializers.IntegerField(
        source="rec_events_count",
        help_text="Number of events attached to this recurring event that occur before the selected event",
    )
    users_avg = RoundedDecimalField(
        source="rec_users_avg",
        help_text="Average number of users who attended previous events under this recurring event",
    )
    users_diff = RoundedDecimalField(
        source="rec_users_diff",
        help_text="Difference between the number of users who attended the selected event and the average users for previous events for the same recurring event",
    )
    members_avg = RoundedDecimalField(
        source="rec_members_avg",
        help_text="Average number of users who attended previous events for the recurring event that were also members of the primary club",
    )
    members_diff = RoundedDecimalField(
        source="rec_members_diff",
        help_text="Difference between the members who attended the selected event and the average members who attended previous events for this recurring event",
    )
    returning_avg = RoundedDecimalField(
        source="rec_returning_avg",
        help_text="Average number of users who attended previous events under this recurring event and also attended prior events for the primary club",
    )
    returning_diff = RoundedDecimalField(
        source="rec_returning_diff",
        help_text="Difference between the returning users for the selected event, and the average for all prior events in the recurring event series",
    )


class EventAnalyticsSerializer(SerializerBase):
    """Information about event attendance, etc."""

    users_total = serializers.IntegerField(
        source="event_users_total",
        help_text="Number of distinct users who submitted the poll for the event",
    )
    members_total = serializers.IntegerField(
        source="event_members_total",
        help_text="Number of users who were members of the primary host",
    )
    returning_total = serializers.IntegerField(
        source="event_returning_total",
        help_text="Number of users who have submitted a poll for the primary club before",
    )

    previous_event = PreviousEventAnalyticsNestedSerializer(source="*")
    event_type = EventTypeAnalyticsNestedSerializer(source="*")
    recurring_event = RecurringEventAnalyticsNestedSerializer(source="*")


class EventDetailSerializer(EventSerializer):
    """Show extended information about an event."""

    analytics = EventAnalyticsSerializer(
        source="_analytics", required=False, allow_null=True, read_only=True
    )

    class Meta:
        model = Event
        fields = EventSerializer.Meta.fields + ["analytics"]


class EventCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCancellation
        fields = "__all__"


class RecurringEventSerializer(ModelSerializerBase):
    """Defines repeating events."""

    attachments = ClubFileNestedSerializer(many=True, required=False)
    is_all_day = serializers.BooleanField(read_only=True)

    class Meta:
        model = RecurringEvent
        fields = "__all__"

    def create(self, validated_data):
        other_clubs = validated_data.pop("other_clubs", [])
        attachments = validated_data.pop("attachments", [])

        # obj = super().create(validated_data)
        obj = RecurringEvent.objects.create(
            **validated_data, other_clubs=other_clubs, attachments=attachments
        )

        return obj


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="February 2026 Heatmap Example",
            response_only=True,
            value={
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "total_events": 20,
                "heatmap": {
                    "2026-02-01": 0,
                    "2026-02-02": 2,
                    "2026-02-03": 1,
                    "2026-02-04": 0,
                    "2026-02-05": 1,
                    "2026-02-06": 0,
                    "2026-02-07": 0,
                    "2026-02-08": 0,
                    "2026-02-09": 2,
                    "2026-02-10": 1,
                    "2026-02-11": 0,
                    "2026-02-12": 1,
                    "2026-02-13": 4,
                    "2026-02-14": 0,
                    "2026-02-15": 0,
                    "2026-02-16": 2,
                    "2026-02-17": 1,
                    "2026-02-18": 0,
                    "2026-02-19": 1,
                    "2026-02-20": 0,
                    "2026-02-21": 0,
                    "2026-02-22": 0,
                    "2026-02-23": 2,
                    "2026-02-24": 1,
                    "2026-02-25": 0,
                    "2026-02-26": 1,
                    "2026-02-27": 0,
                    "2026-02-28": 0,
                },
            },
        )
    ]
)
class EventHeatmapSerializer(SerializerBase):
    """Show event count for each day."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_events = serializers.IntegerField()
    heatmap = serializers.DictField(child=serializers.IntegerField())


#############################################################
# MARK: CSV Serializers
#############################################################


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
        except Event.DoesNotExist as e:
            raise serializers.ValidationError(
                "Event with the given name, start_at and end_at does not exist."
            ) from e

        attrs["event"] = event
        return attrs

    def create(self, validated_data):
        validated_data.pop("name", None)
        validated_data.pop("start_at", None)
        validated_data.pop("end_at", None)
        return super().create(validated_data)
