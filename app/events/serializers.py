from clubs.models import Club
from clubs.serializers import ClubFileNestedSerializer
from core.abstracts.serializers import ModelSerializerBase, SerializerBase
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
        exclude = ["clubs", "make_public_task"]

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

        # Temporarily disable enable_attendance
        enable_attendance = instance.enable_attendance
        validated_data["enable_attendance"] = False
        event = super().update(instance, validated_data)

        if has_poll and event.poll != poll:
            event.poll = poll
        event.refresh_from_db()

        # Re-enable enable_attendance
        event.enable_attendance = enable_attendance
        event.save()

        event.attachments.clear()

        for attachment in attachment_data:
            attachment_id = attachment["id"]
            event.attachments.add(attachment_id)

        return event


class EventAnalyticsSerializer(EventSerializer):
    analytics = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    def get_analytics(self, obj: Event):
        """Returns desired analytics from an event object"""
        request = self.context.get("request")
        if not request or not request.user.has_perm(
            "events.view_event_analytics", is_global=False
        ):
            return None
        return {
            "total_attended_users": obj.attendances.count(),
            "total_poll_submissions": 0
            if obj.submissions is None
            else obj.submissions.count(),
        }

    def get_permissions(self, obj: Event):
        """Returns permissions for an event an object"""
        request = self.context.get("request")
        can_view_analytics = request and request.user.has_perm(
            "events.view_event_analytics", is_global=False
        )
        return {"can_view_analytics": can_view_analytics}


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
    # heatmap = serializers.DictField()


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
