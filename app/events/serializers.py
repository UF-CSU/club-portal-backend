from rest_framework import serializers

from clubs.models import Club
from core.abstracts.serializers import ModelSerializerBase
from events.models import Event, EventCancellation, EventHost, EventTag
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404


class EventTagSerializer(ModelSerializerBase):
    """Represents a tag event for all clubs"""

    class Meta:
        fields = '__all__'


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
        source="club.logo",
        read_only=True,
    )

    is_primary = serializers.BooleanField(default=False)

    class Meta:
        model = EventHost
        fields = ["club_id", "club_name", "club_logo", "is_primary"]


class EventSerializer(ModelSerializerBase):
    """Represents a calendar event for a single or multiple clubs."""

    hosts = EventHostSerializer(many=True)
    all_day = serializers.BooleanField(read_only=True)
    tags = EventTagSerializer(many=True, required=False)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "description",
            "location",
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
        tag_data = validated_data.pop("tags", [])

        print(tag_data)

        event = Event.objects.create(**validated_data)

        for host in hosts_data:
            EventHost.objects.create(
                event=event, club=host["club"], is_primary=host.get("is_primary", False)
            )
        
        for tag in tag_data:
            tag_obj = tag.get("id")
            tag_fields = model_to_dict(tag_obj)
            print(tag_fields)
            tag_id = tag_fields["id"]
            print(tag_id)
            new_tag = get_object_or_404(EventTag, id=tag_id)
            if new_tag:
                event.tags.add(new_tag)

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
