from django.core import exceptions
from rest_framework import serializers

from clubs.models import Club
from clubs.serializers import ClubFileNestedSerializer
from core.abstracts.serializers import ModelSerializerBase
from events.models import (
    Event,
    EventAttendance,
    EventAttendanceLink,
    EventCancellation,
    EventHost,
    EventTag,
    RecurringEvent,
)
from events.tasks import sync_recurring_event_task
from lib.celery import delay_task
from polls.models import Poll
from polls.serializers import EventPollField
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from users.models import User


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


class EventSerializer(ModelSerializerBase):
    """Represents a calendar event for a single or multiple clubs."""

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
    attachments = ClubFileNestedSerializer(many=True, required=False)
    poll = EventPollField(queryset=Poll.objects.all(), required=False, allow_null=True)
    attendance_links = EventAttendanceLinkSerializer(many=True, required=False)

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

        event = Event.objects.create(**validated_data)

        if poll:
            event.poll = poll
            event.save()

        for host in hosts_data:

            EventHost.objects.create(
                event=event, club=host["club"], is_primary=host.get("is_primary", False)
            )

        for attachment in attachment_data:
            attachment_id = attachment["id"]

            event.attachments.add(attachment_id)

        event.tags.set(validated_tags)

        return event

    def update(self, instance, validated_data):
        attachment_data = validated_data.pop("attachments", [])

        event = super().update(instance, validated_data)

        event.attachments.clear()

        for attachment in attachment_data:
            attachment_id = attachment["id"]
            event.attachments.add(attachment_id)

        return event


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
        obj = super().create(validated_data)
        delay_task(sync_recurring_event_task, recurring_event_id=obj.id)

        return obj


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
